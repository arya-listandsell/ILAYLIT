import requests
from PIL import Image
from io import BytesIO
import pandas as pd

df_input = pd.read_csv('final_output_04_06_2025.csv')

broken_image_logs = []

def is_image_url_working(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200 and 'image' in response.headers.get('Content-Type', '')
    except requests.RequestException:
        return False

for i, url in df_input['Image Src'].items():
    if pd.isna(url) or url.strip() == "":
        continue

    if not is_image_url_working(url):
        df_input.at[i, 'Image Src'] = ''
        broken_image_logs.append({'URL': url, 'Reason': 'Broken image'})
        print(f"Removed {url} - Broken image")
    else:
        try:
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            width, height = img.size

            if width > 3500:
                df_input.at[i, 'Image Src'] = ''
                broken_image_logs.append({'URL': url, 'Reason': f'Resolution too high: {width}x{height}'})
                print(f"Removed {url} - High resolution: {width}x{height}")
        except Exception as e:
            df_input.at[i, 'Image Src'] = ''
            broken_image_logs.append({'URL': url, 'Reason': f'Failed to load: {e}'})
            print(f"Removed {url} - Failed to load. Reason: {e}")

df_input.to_csv('final_output_cleaned_3500.csv', index=False)

if broken_image_logs:
    pd.DataFrame(broken_image_logs).to_excel('image_url_report_3500.xlsx', sheet_name='Broken Images', index=False)
    print("Broken image log saved as: image_url_report_3500.xlsx")
else:
    print("No broken images found. Excel log not created.")

print("Cleaning complete. File saved as 'final_output_cleaned_3500.csv'")
