---
description: Deploy changes to production EC2 server
---
// turbo-all

1. Build the frontend
```bash
cd /Users/ifthikaraliseyed/Desktop/FTB_APP/ftb-api-26/frontend && npm run build
```

2. Commit and push changes
```bash
cd /Users/ifthikaraliseyed/Desktop/FTB_APP/ftb-api-26 && git add -A && git commit -m "deploy: update" && git push origin main
```

3. Pull on server and rebuild
```bash
ssh -o ConnectTimeout=10 -i /Users/ifthikaraliseyed/Desktop/FTB_APP/fynda-deploy.pem ubuntu@100.31.135.211 "cd /opt/fetchbot/ftb-api-26 && git pull origin main && docker compose -f docker/docker-compose.prod.yml up -d --build web frontend nginx"
```
