# FTG Modules web
Cool-looking web interface for your modules

![image](https://user-images.githubusercontent.com/36935426/164723131-e7db978b-e1bc-4df2-9694-9ae6cfe96c1f.png)

### Working demo: https://mods.hikariatama.ru
# Setup
1. Change options in `config.json`
2. Setup reverse proxy if needed
3. Start with `gunicorn -w 3 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:1391` (change port if needed)

You're good to go!
