automated-youtube-shorts-uploader agent completely free

Hey guys its me sufyan i created a completely free to use agent that can upload shorts on youtbe based on the topics you give it i will try to explain each step carefully and i will be using my workflow to explain you the steps you can just twik it a little bit and use it according to your needs lets start

1. Download all the files inside agent folder from my repo

2. Install the base tools 
Node.js
python 3.10+
FFmpeg-> winget install ffmpeg(windows cmd)

3.start the ffmpeg microservice

cd /agent/files
pip install -r requirements.txt
python app1.py

Leave this terminal open. Visit `http://localhost:5000/health` in a browser
— you should see `{"status":"ok"}`. This is the service that turns images +
audio into the final video; the n8n workflow calls it on `localhost:5000`

3.get your api keys 
https://aistudio.google.com/ -> create an account and the create api and save it somewhere we will use it later

ELEVENLABS:go to elevenlabs.io and create an account then create an api key and save it somewhere now the important part elevenlabs will not let you use its voice from voice library for free through api but guess what i have a way to use voice through api so choose any voice of your liking and copy the voice description every voice has its description like(a little british girl with warm voice and depth so and so) copy that and go to create my own voice using a promt paste the description and create it will take 300 credit from your initial 10000 credit (cheap deal) now that you have created your own voice u can use it through api copy its voice id and save it we will use it later

4. Build google sheet(i'm building according to my project u can change the topic according to yours)

**`Control`** (row 1 = headers, row 2 = data):
| Status |
|---|
| active |

**`StoryBank`** (row 1 = headers):
| ID | Title | Type | SourceText | Used | LastUsedDate | VideoURL |
|---|---|---|---|---|---|---|

Add at least 10-20 rows to start (`Used` = false' for all of them) — public
domain fables (Aesop, Panchatantra), folk tales, or nursery rhymes.
`SourceText` can just be the plain text of the story, 100-300 words is
plenty; the AI condenses it. Copy the Sheet's ID from its URL — the long
string between `/d/` and `/edit`

5.Install n8n and import the workflow(some nodes will need some changes which i will clarify here so don't leave yet otherwise agent will fail)

npm install n8n -g
n8n start

import the workflow by file (daily-story-shorts-youtube.json)

------------------------------------x------------------------------------
node->AI: Script + Video Prompt + Metadata (Gemini)
URL->https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent
Headers->x-goog-api-key and value = your api key from https://aistudio.google.com/
JSON->
{{ JSON.stringify({
  system_instruction: {
    parts: [{ text: "You write tight, visual scripts for 45-55 second narrated YouTube Shorts based on classic public-domain stories/rhymes. Output ONLY valid JSON, no markdown fences, matching this schema: {\"narration\": string (<=130 words, simple spoken language), \"scenes\": [{\"description\": string (a single detailed image prompt: subject, setting, art style, lighting), \"duration_seconds\": number}], \"title\": string (<=70 chars), \"description\": string (150-300 words, hook + summary + CTA + 3-5 hashtags), \"tags\": [string] (12-18 tags), \"thumbnail_text\": string (<=5 words)}. Aim for 6-9 scenes of 5-7 seconds each. Keep art style consistent across scenes, e.g. warm watercolor storybook illustration." }]
  },
  contents: [{
    role: "user",
    parts: [{ text: "Source material title: " + $json.Title + "\nType: " + $json.Type + "\nSource text:\n" + $json.SourceText }]
  }]
}) }}

node->Generate Narration Audio (TTS)
URL->https://api.elevenlabs.io/v1/text-to-speech/THE_VOICE_ID_YOU_CREATED
Authentication-> generic credential type
generic auth type->header auth
JSON->
{{ JSON.stringify({ text: $json.narration, model_id: "eleven_multilingual_v2" }) }}


node->Encode Audio Base64
javascript-> 
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data');
return [{ json: { audio_base64: buffer.toString('base64') } }];

node->Generate Scene Image (Pollinations.ai)
URL->https://image.pollinations.ai/prompt/{{ encodeURIComponent(($json.scenes?.description || $json.description || 'storybook scene') + ', warm watercolor storybook illustration, no text') }}

batching:
items per batch:1
batch interval: 20000 or more

node->collect all scene Images
javascript->
const items = $input.all();
const images = [];
for (let i = 0; i < items.length; i++) {
  const buffer = await this.helpers.getBinaryDataBuffer(i, 'data');
  images.push(buffer.toString('base64'));
}
return [{ json: { images } }];

---------------------------x---------------------------

Now click on personal and go to credentials -> create credentials choose
google sheets OAuth2 API
copy->OAuth Redirect URL
now go to https://console.cloud.google.com/ -> create account(after)->new projct -> API and SERVICES
search -> Google Sheets API -> enable it then
OAuth consent screen → User type: External → fill the minimum required fields → Save. It'll start in **Testing** status then go to
 Credentials → Create Credentials → OAuth client ID
 → Application type: Web application → Authorized redirect URI:paste the OAuth Redirect URL you copied from n8n credentials section and save it also very important(save the client_ID,client_secret)
now go back to credentials section on n8n paste the client_ID and client_secret and connect with your gmail account ->
IMPORTANT->Under OAuth consent screen → Test users, add your own Google account's
     email — required while status is "Testing."
FINISHED

again create credentials in n8n->select Youtube OAuth2 API 
copy-> OAuth Redirect URL 
go to https://console.cloud.google.com/ ->API services->
search->YouTube Data API v3 (enable) do the same steps as google sheets api if not done since same secret and client key is required
FINISHED

IMPORTANT->Google Cloud Console → APIs & Services → OAuth consent screen → find 'Data Access' (or 'Scopes') → Add or Remove Scopes → search 'youtube' → check the box for '.../auth/youtube.upload' (and youtube.readonly if shown) → tick the box Update → Save





node->Check Control Sheet (Pause Switch)
credential->choose google sheet Oauth2 api
Document:
by ID-> paste the sheet id of Control sheet which you saved earlier


node->Get Unused Stories
credential->choose google sheet Oauth2 api
Document:
by ID-> paste the sheet id of StoryBank sheet which you saved earlier
filter1:
Column:Used
Value:false'

node->Upload to youtube -> check if the credentials is set to Youtube OAuth2 api

AND WE ARE DONE 
EXECUTE THE WORKFLOW IT SHOULD RUN WITHOUT ANY NODE FAILING
AND THERE YOU HAVE IT A COMPLETELY FREE AGENT THAT GENERATES NARRATION,CREATE IMAGES MERGE THEM AND CREATE A SHORT VIDEO BASED ON CONTEXT AND UPLOADS IT TO YOUTUBE IN ONE CLICK

NOTE: next day you need to start python app1.py and n8n start then execute the workflow(one click) to again upload a new short



