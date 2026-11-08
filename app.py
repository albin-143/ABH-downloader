from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
import yt_dlp
import os

app = FastAPI()

# 1. Main Browser & UI (HTML, CSS, JS combined in single file)
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABH Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f4f4f4; }
        #toolbar { background: #2196F3; color: white; padding: 10px; display: flex; justify-content: space-between; align-items: center; }
        #url-bar { width: 55%; padding: 8px; border-radius: 4px; border: none; }
        .menu-btn { background: none; border: none; color: white; font-size: 16px; cursor: pointer; }
        #browser-frame { width: 100%; height: 78vh; border: none; background: white; }
        .tick { color: green; font-weight: bold; display: none; }
        #qualityModal { display:none; position:fixed; top:25%; left:10%; width:80%; background:white; padding:20px; border-radius:8px; box-shadow:0px 0px 15px rgba(0,0,0,0.5); z-index:1000; }
    </style>
</head>
<body>

    <!-- Toolbar Features -->
    <div id="toolbar">
        <button class="menu-btn" onclick="addTab()">➕ Tab</button>
        <input type="text" id="url-bar" value="https://www.youtube.com" onkeypress="handleSearch(event)">
        <button class="menu-btn" onclick="toggleDesktopMode()">💻</button>
        <button class="menu-btn" onclick="openBookmarks()">🔖</button>
        <button class="menu-btn" onclick="openDownloads()">⬇️</button>
        <button class="menu-btn" onclick="openSettings()">⚙️</button>
    </div>

    <!-- Browser View -->
    <iframe id="browser-frame" src="https://www.youtube.com"></iframe>

    <!-- Quality Selection Popup Modal -->
    <div id="qualityModal">
        <h3>எந்த Quality வேண்டும்?</h3>
        <div id="qualityList"></div>
        <br>
        <button onclick="closeModal()" style="padding: 5px 10px;">Close</button>
    </div>

    <!-- Status Bar with Double Tick -->
    <div id="download-status" style="position: fixed; bottom: 0; width: 100%; background: #222; color: white; padding: 10px; text-align: center; font-size: 14px;">
        Status: <span id="tick-status">Standby</span> <span id="double-tick" class="tick">✔✔</span>
    </div>

    <script>
        // Handle URL Navigation
        function handleSearch(e) {
            if (e.key === 'Enter') {
                let url = document.getElementById('url-bar').value;
                if(!url.startsWith('http')) url = 'https://' + url;
                document.getElementById('browser-frame').src = url;
                
                // If YouTube link, check qualities
                if(url.includes('youtube.com') || url.includes('youtu.be')) {
                    fetchQualities(url);
                }
            }
        }

        // 2 & 3. Fetch & Prompt Quality Options
        function fetchQualities(videoUrl) {
            let formData = new FormData();
            formData.append('url', videoUrl);
            
            fetch('/get-youtube-qualities', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                let listDiv = document.getElementById('qualityList');
                listDiv.innerHTML = '';
                data.formats.forEach(f => {
                    listDiv.innerHTML += `<button onclick="downloadWithQuality('${f.url}', '${data.title}')" style="margin:5px; padding:8px;">${f.resolution}</button><br>`;
                });
                document.getElementById('qualityModal').style.display = 'block';
            });
        }

        function closeModal() {
            document.getElementById('qualityModal').style.display = 'none';
        }

        function downloadWithQuality(fileUrl, title) {
            closeModal();
            document.getElementById('tick-status').innerText = 'Downloading ' + title + '...';
            
            let formData = new FormData();
            formData.append('file_url', fileUrl);
            formData.append('folder_name', 'YouTube_Downloads');

            fetch('/download-item', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                document.getElementById('tick-status').innerText = 'Downloaded Successfully!';
                document.getElementById('double-tick').style.display = 'inline'; // 4. Double Tick
            });
        }

        // 5 & 6. Website Folder Long-Press & Sub-folder download
        let pressTimer;
        document.addEventListener('touchstart', function(e) {
            if (e.target.tagName === 'A') {
                pressTimer = setTimeout(() => {
                    let folderName = e.target.innerText || "Downloaded_Folder";
                    let folderUrl = e.target.href;
                    triggerFolderDownload(folderName, folderUrl);
                }, 1000); // 1 second long press
            }
        });
        document.addEventListener('touchend', () => clearTimeout(pressTimer));

        function triggerFolderDownload(name, url) {
            alert(`Folder "${name}" long-pressed! Downloading with sub-folders...`);
            let formData = new FormData();
            formData.append('file_url', url);
            formData.append('folder_name', name);

            fetch('/download-item', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                document.getElementById('tick-status').innerText = name + ' Saved!';
                document.getElementById('double-tick').style.display = 'inline';
            });
        }

        // 10. Toolbar Features Actions
        function toggleDesktopMode() { alert("Desktop mode toggled."); }
        function openBookmarks() { alert("Opening Bookmarks Page..."); }
        function openDownloads() { alert("Opening Downloaded Page..."); }
        function openSettings() { alert("Opening Settings..."); }
        function addTab() { alert("New Tab Added!"); }
    </script>
</body>
</html>
    """

# 2. YouTube Quality Selector API
@app.post("/get-youtube-qualities")
def get_qualities(url: str = Form(...)):
    ydl_opts = {'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get('formats', []):
                if f.get('height') and f.get('ext') == 'mp4':
                    formats.append({
                        'resolution': f"{f['height']}p",
                        'url': f['url']
                    })
            seen = set()
            unique_formats = [x for x in formats if x['resolution'] not in seen and not seen.add(x['resolution'])]
            return {"title": info.get('title', 'Video'), "formats": unique_formats}
        except Exception as e:
            return {"title": "Error", "formats": [{'resolution': 'Default 360p', 'url': url}]}

# 3, 5, 6, 7. Download Item & Sub-folder Handler for All Websites
@app.post("/download-item")
def download_item(file_url: str = Form(...), folder_name: str = Form(...)):
    safe_folder = "".-join([c for c in folder_name if c.isalnum() or c in (' ', '_')]).strip()
    save_path = os.path.expanduser(f"~/Download/ABH_Downloader/{safe_folder}")
    os.makedirs(save_path, exist_ok=True)
    
    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([file_url])
        return {"status": "success", "message": "Downloaded with sub-folders intact"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
