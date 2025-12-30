# Google Sheets Authentication Setup Guide

If you want to keep your Google Sheet private, you'll need to set up authentication using a Google Service Account.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Note your project name

## Step 2: Enable Google Sheets API

1. In Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Sheets API"
3. Click on it and click "Enable"

## Step 3: Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Give it a name (e.g., "pittsburgh-map-service")
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

## Step 4: Create and Download Credentials

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Download the JSON file
6. Save it in your project directory (e.g., `google_credentials.json`)

## Step 5: Share Your Google Sheet with the Service Account

1. Open the downloaded JSON file
2. Find the `client_email` field (looks like: `your-service@project-id.iam.gserviceaccount.com`)
3. Copy that email address
4. Open your Google Sheet
5. Click "Share" button
6. Paste the service account email
7. Give it "Viewer" permission
8. Click "Send" (you can uncheck "Notify people" if you want)

## Step 6: Update Your Code

Update the `main()` function in `pittsburgh_map.py`:

```python
pittsburgh_map.load_leap_locations_from_google_sheets(
    sheet_id=google_sheet_id,
    sheet_names=None,
    use_public_export=False,  # Change to False
    credentials_path="google_credentials.json",  # Path to your JSON file
    skip_duplicates=True
)
```

## Security Note

⚠️ **Important**: Never commit the `google_credentials.json` file to version control (Git). Add it to your `.gitignore` file:

```
google_credentials.json
```

