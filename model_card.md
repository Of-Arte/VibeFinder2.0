# VibeFinder 2.0 — Reflection and Ethics

## Limitations
The LLM classifier is a key component created to test replacing paid third-party music APIs after encountering access friction. Because the classifier estimates song attributes from titles and artists instead of listening to raw audio, it can mislabel obscure songs. Additionally, the track pool retrieved from public APIs favors mainstream artists, creating a bias toward popular music.

## Misuse and Prevention
- **Misuse Case**: An AI that dynamically generates recommendations based on user inputs could be tricked via prompt injection into generating inappropriate, hateful, or off-brand content if untrusted free-text (such as the user's name or song title) were fed into the prompt.
- **Prevention**: We keep untrusted text out of the LLM prompts as much as possible. The only free-text field is the user's name, and it is never sent to any Gemini call. Everything that reaches the model is from a fixed curated list of options, so the model always has safe context. Finally, all Gemini calls use strict JSON output and Pydantic validation, which acts as a guardrail against the LLM breaking out of its classification role.

## Surprises
I was surprised how consistent the energy levels matched my expectations for the artists selected. Even though the model does not have access to audio features, it was able to predict the energy level of the songs based on the artist and song name alone. To maintain reliability, I limited the number of songs and used a curated list of 16 popular artists to choose from.

## AI Collaboration
- **Helpful Suggestion**: When designing the architecture, AI suggested using API's like deezer or spotify to fetch songs and also suggested using gemini flash for classification task. This was a good suggestion as it helped me create a broader system outside the limitations of the initial csv file.
- **Flawed Suggestion**: Initially, the AI suggested fetching songs from Spotify's recommendation endpoint, which require user authentication. It failed to account for the lack of access to that specific endpoint for general users, which was a roadblock. This led me to using deezer as the main API. Additionally, the AI suggested using gemini flash for classification task which was a good suggestion, but it failed to account for the lack of access to the gemini-2.5-flash-lite model for new users. 
