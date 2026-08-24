# Automated YouTube Shorts Uploader — 100% Free

Hey, it's Sufyan. This is a completely free-to-use agent that automatically generates and uploads YouTube Shorts based on topics you give it. Below is my exact workflow — tweak it to fit your own use case.

It uses AI to write a script, generates narration audio, generates scene images, stitches everything into a video, and uploads it straight to YouTube — all in one click.

**Stack:** n8n · Gemini (script/metadata) · ElevenLabs (TTS) · Pollinations.ai (images) · FFmpeg (video assembly) · Google Sheets (story queue) · YouTube Data API v3

---

## 1. Get the files

Download all the files inside the `agent` folder from my repo.

## 2. Install the base tools

- [Node.js](https://nodejs.org/)
- Python 3.10+
- FFmpeg — `winget install ffmpeg` (Windows CMD)

## 3. Start the FFmpeg microservice

This is the service that turns images + audio into the final video. The n8n workflow calls it on `localhost:5000`.

```bash
cd /agent/files
pip install -r requirements.txt
python app1.py
```

Leave this terminal open. Visit `http://localhost:5000/health` in a browser — you should see `{"status":"ok"}`.

## 4. Get your API keys

**Gemini**
Go to [aistudio.google.com](https://aistudio.google.com/), create an account, create an API key, and save it — you'll need it later.

**ElevenLabs**
Go to [elevenlabs.io](https://elevenlabs.io) and create an account, then create an API key.

ElevenLabs won't let you use voices from its Voice Library through the API for free — but there's a workaround. Pick any voice you like from the library and copy its description (e.g. *"a little British girl with a warm voice and depth"*). Then go to **Create my own voice using a prompt**, paste that description, and generate it. This costs ~300 credits from your initial 10,000 (a good deal). Once created, copy the voice ID — you'll need it for the TTS API call.

## 5. Build the Google Sheet

Set up two tabs (change the topic/columns to fit your own project — this is what I used):

**`Control`** (row 1 = headers, row 2 = data)

| Status |
|---|
| active |

**`StoryBank`** (row 1 = headers)

| ID | Title | Type | SourceText | Used | LastUsedDate | VideoURL |
|---|---|---|---|---|---|---|

Add at least 10–20 rows to start (`Used` = `false` for all of them) — public domain fables (Aesop, Panchatantra), folk tales, or nursery rhymes work well. `SourceText` can just be the plain story text, 100–300 words is plenty; the AI condenses it.

Copy each sheet's ID from its URL — the long string between `/d/` and `/edit`.

## 6. Install n8n and import the workflow

```bash
npm install n8n -g
n8n start
```

Import the workflow by file: `daily-story-shorts-youtube.json`.

A few nodes need manual configuration after import — details below, don't skip these or the workflow will fail.

---

## Workflow node configuration

### AI: Script + Video Prompt + Metadata (Gemini)

- **URL:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent`
- **Headers:** `x-goog-api-key` = your Gemini API key
- **Body:**

```js
{{ JSON.stringify({
  system_instruction: {
    parts: [{ text: "You write tight, visual scripts for 45-55 second narrated YouTube Shorts based on classic public-domain stories/rhymes. Output ONLY valid JSON, no markdown fences, matching this schema: {\"narration\": string (<=130 words, simple spoken language), \"scenes\": [{\"description\": string (a single detailed image prompt: subject, setting, art style, lighting), \"duration_seconds\": number}], \"title\": string (<=70 chars), \"description\": string (150-300 words, hook + summary + CTA + 3-5 hashtags), \"tags\": [string] (12-18 tags), \"thumbnail_text\": string (<=5 words)}. Aim for 6-9 scenes of 5-7 seconds each. Keep art style consistent across scenes, e.g. warm watercolor storybook illustration." }]
  },
  contents: [{
    role: "user",
    parts: [{ text: "Source material title: " + $json.Title + "\nType: " + $json.Type + "\nSource text:\n" + $json.SourceText }]
  }]
}) }}
```

### Generate Narration Audio (TTS)

- **URL:** `https://api.elevenlabs.io/v1/text-to-speech/THE_VOICE_ID_YOU_CREATED`
- **Authentication:** Generic Credential Type → Generic Auth Type → Header Auth
- **Body:**

```js
{{ JSON.stringify({ text: $json.narration, model_id: "eleven_multilingual_v2" }) }}
```

### Encode Audio Base64

```js
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data');
return [{ json: { audio_base64: buffer.toString('base64') } }];
```

### Generate Scene Image (Pollinations.ai)

- **URL:**

```
https://image.pollinations.ai/prompt/{{ encodeURIComponent(($json.scenes?.description || $json.description || 'storybook scene') + ', warm watercolor storybook illustration, no text') }}
```

- **Batching:** items per batch = `1`, batch interval = `20000` ms or more

### Collect All Scene Images

```js
const items = $input.all();
const images = [];
for (let i = 0; i < items.length; i++) {
  const buffer = await this.helpers.getBinaryDataBuffer(i, 'data');
  images.push(buffer.toString('base64'));
}
return [{ json: { images } }];
```

---

## Google credentials (Sheets + YouTube)

### Google Sheets OAuth2

1. In n8n: **Credentials → Create Credential → Google Sheets OAuth2 API**, then copy the **OAuth Redirect URL**.
2. In [Google Cloud Console](https://console.cloud.google.com/): create an account → new project → **APIs & Services**.
3. Search **Google Sheets API** → Enable.
4. **OAuth consent screen** → User type: **External** → fill the minimum required fields → Save. It starts in **Testing** status.
5. **Credentials → Create Credentials → OAuth client ID** → Application type: **Web application** → Authorized redirect URI: paste the OAuth Redirect URL from n8n → Save.
6. Save the **Client ID** and **Client Secret**.
7. Back in n8n, paste the Client ID/Secret into the credential and connect your Google account.
8. **Important:** under **OAuth consent screen → Test users**, add your own Google account email — required while status is "Testing."

### YouTube OAuth2

1. In n8n: **Credentials → Create Credential → YouTube OAuth2 API**, copy the **OAuth Redirect URL**.
2. In Google Cloud Console: **APIs & Services** → search **YouTube Data API v3** → Enable.
3. Repeat the same OAuth consent/credential steps as above (same Client ID/Secret can be reused if already set up).
4. **Important:** Google Cloud Console → **APIs & Services → OAuth consent screen** → **Data Access** (or **Scopes**) → **Add or Remove Scopes** → search "youtube" → check `.../auth/youtube.upload` (and `youtube.readonly` if shown) → Update → Save.

---

## Final nodes

**Check Control Sheet (Pause Switch)**
- Credential: Google Sheets OAuth2 API
- Document → By ID → paste the `Control` sheet ID

**Get Unused Stories**
- Credential: Google Sheets OAuth2 API
- Document → By ID → paste the `StoryBank` sheet ID
- Filter: `Used` = `false`

**Upload to YouTube**
- Credential: YouTube OAuth2 API

---

## You're done

Execute the workflow — it should run without any node failing. You now have a completely free agent that:

1. Generates a narration script + scene prompts + metadata from your story bank
2. Creates narration audio via TTS
3. Generates scene images
4. Merges everything into a short video via the FFmpeg microservice
5. Uploads it to YouTube automatically

### Daily use

Each day, just start the two services and run the workflow once:

```bash
python app1.py     # FFmpeg microservice
n8n start           # n8n
```

Then execute the workflow — one click, new Short uploaded.
