import os
import time
import base64
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

class MeetingRecorder:
    def __init__(self, video_id, meeting_url):
        self.video_id = video_id
        self.meeting_url = meeting_url
        self.driver = None

    def get_driver(self):
        options = uc.ChromeOptions() 
        options.add_experimental_option("prefs", { \
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.notifications": 1
        })
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--enable-usermedia-screen-capturing")
        options.add_argument("--auto-select-desktop-capture-source=Entire screen")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--mute-audio")
        # options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        options.add_argument("--disable-extensions") 
        options.add_argument("--window-size=1080,720")
        # #ptions.add_argument("--headless=new")  # Optional: Run in headless mode

# 
        self.driver = uc.Chrome(options=options, use_subprocess=False, enable_cdp_events=True, headless=True)
        # self.driver.set_window_size(1280, 720)

    def join_meeting(self):
        # self.driver.get("https://accounts.google.com/")
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": '''
              Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                 })
            '''
        })
        self.driver.get(self.meeting_url)
        self.driver.save_screenshot("1.png")

        wait = WebDriverWait(self.driver, 20)
        try:
            got_it_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Got it']")))
            ActionChains(self.driver).move_to_element(got_it_button).perform()
            got_it_button.click()
        except:
            pass  # 'Got it' button may not appear

        try:
            name_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Your name']")))
            ActionChains(self.driver).move_to_element(name_input).perform()
            name_input.send_keys("Recalify Bot")
        except:
            pass  # Name input may not be required if already signed in

        try:
            join_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Ask to join']")))

            ActionChains(self.driver).move_to_element(join_button).perform()
            join_button.click()
        except:
            pass  # 'Ask to join' button may not appear if auto-admitted

    def start_recording(self):
        backend_url = os.environ.get("BACKEND_URL")
        video_id = self.video_id

        js_script = f"""
        (function() {{
            const backendURL = "{backend_url}";
            const videoId = "{video_id}";

            async function uploadStream(blob, partNumber) {{
                await fetch(`${{backendURL}}/api/v1/upload-streamFile/upload`, {{
                    method: "POST",
                    headers: {{
                        "X-Upload-Id": videoId,
                        "x-part-number": partNumber.toString(),
                    }},
                    body: blob,
                }});
            }}

            function findNumberOfParticipants() {{
                const peopleButton = document.querySelector('[aria-label="Show everyone"]');
                if (peopleButton) {{
                    peopleButton.click();
                    const participantsText = document.querySelector('[aria-label^="Participants"]')?.innerText;
                    const match = participantsText?.match(/\\d+/);
                    return match ? parseInt(match[0], 10) : 0;
                }}
                return 0;
            }}

            async function startRecord() {{
                try {{
                    const res = await fetch(`${{backendURL}}/api/v1/upload-streamFile/start`, {{
                        method: "POST",
                        headers: {{
                            "X-Upload-Id": videoId,
                        }},
                    }});
                    return res.ok;
                }} catch (error) {{
                    return false;
                }}
            }}

            async function stopRecording() {{
                try {{
                    const response = await fetch(`${{backendURL}}/api/v1/upload-streamFile/stop`, {{
                        method: "PATCH",
                        headers: {{
                            "X-Upload-Id": videoId,
                        }},
                    }});
                    return response.ok;
                }} catch (error) {{
                    return false;
                }}
            }}

            function startRecording(stream) {{
                return new Promise((resolve, reject) => {{
                    let recorder = new MediaRecorder(stream);
                    let partNumber = 1;
                    recorder.ondataavailable = async (event) => {{
                        const participants = findNumberOfParticipants();
                        if (participants === 1) {{
                            await stopRecording();
                            recorder.stop();
                            return;
                        }}
                        await uploadStream(event.data, partNumber);
                        partNumber += 1;
                    }};
                    recorder.onerror = (event) => {{
                        reject();
                    }};
                    recorder.onstop = () => {{
                        resolve("Recorded successfully.");
                    }};
                    recorder.start(30000);
                }});
            }}

            navigator.mediaDevices.getDisplayMedia({{
                video: {{
                    displaySurface: "browser",
                }},
                audio: true,
                preferCurrentTab: true,
            }})
            .then(async (screenStream) => {{
                const audioContext = new AudioContext();
                const dest = audioContext.createMediaStreamDestination();

                const screenAudio = audioContext.createMediaStreamSource(screenStream);
                screenAudio.connect(dest);

                const combinedStream = new MediaStream([
                    ...screenStream.getVideoTracks(),
                    ...dest.stream.getAudioTracks(),
                ]);

                const started = await startRecord();
                if (started) {{
                    await startRecording(combinedStream);
                }}

                screenStream.getTracks().forEach((track) => track.stop());
            }});
        }})();
        """

        self.driver.execute_script(js_script)

    def start(self):
        try:
             self.get_driver()
             self.join_meeting()
             time.sleep(5)  # Wait for the meeting interface to load
             self.start_recording()
        except Exception as e:
            print(f"[ERROR] Failed to start the meeting automation: {e}")
 


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python meeting_recorder.py <video_id> <meeting_url>")
        sys.exit(1)

    video_id = sys.argv[1]
    meeting_url = sys.argv[2]

    recorder = MeetingRecorder(video_id, meeting_url)
    recorder.start()
