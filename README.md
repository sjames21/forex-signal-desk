# FX Signal Desk
Mobile-friendly Streamlit forex signal scanner using Twelve Data's free market data API.

## Deploy from a phone
1. Create a GitHub repository (private recommended) using github.com in your phone browser.
2. Upload `streamlit_app.py` and `requirements.txt` from this ZIP to the root of the repository.
3. Go to https://share.streamlit.io, sign in with GitHub, create a new app, select your repository, branch `main`, and main file `streamlit_app.py`.
4. In **Advanced settings > Secrets**, paste `TWELVE_DATA_API_KEY = "YOUR_KEY_HERE"` (replace placeholder with your actual Twelve Data API key). Do not add this secret to GitHub.
5. Deploy, open the resulting streamlit.app URL, and tap **Scan market**. On iPhone Safari, use Share > Add to Home Screen for app-like access.

Free plan credits are limited; each scan uses one time_series request per selected pair. Refresh manually to conserve credits. This is not an always-running scanner or push-alert service.
