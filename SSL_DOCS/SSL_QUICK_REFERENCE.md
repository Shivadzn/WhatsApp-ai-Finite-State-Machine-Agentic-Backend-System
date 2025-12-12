# 🔒 SSL Quick Reference Card

## 🎯 Recommended Setup

```
Internet → Cloudflare (SSL/CDN) → Nginx (Reverse Proxy) → FastAPI (HTTP)
```

**Why?**
- ✅ Free SSL forever
- ✅ Auto-renewal
- ✅ DDoS protection
- ✅ CDN acceleration
- ✅ Easy setup

---

## ⚡ Quick Setup (5 Minutes)

### 1. Cloudflare Setup
```bash
1. Sign up at cloudflare.com
2. Add your domain
3. Update nameservers
4. SSL/TLS → Full (strict)
5. Done!
```

### 2. Nginx Reverse Proxy
```bash
# Install Nginx
sudo apt install nginx -y

# Create config
sudo nano /etc/nginx/sites-available/ai-backend
```

**Paste this config:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Get Certificate
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Done! Auto-renewal is set up automatically
```

### 4. Start FastAPI
```bash
# No SSL config needed (Nginx handles it)
python run_server.py
```

---

## 🔧 Environment Variables

### With Nginx (Recommended)
```bash
# .env
ENVIRONMENT=production
# No SSL_CERTFILE or SSL_KEYFILE needed
```

### Direct SSL (Not Recommended)
```bash
# .env
ENVIRONMENT=production
SSL_CERTFILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEYFILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

---

## ✅ Testing Checklist

```bash
# 1. Test HTTPS
curl -I https://yourdomain.com/health

# 2. Test SSL Labs (A+ rating)
# Visit: https://www.ssllabs.com/ssltest/

# 3. Test WhatsApp Webhook
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# 4. Check certificate expiry
sudo certbot certificates

# 5. Test auto-renewal
sudo certbot renew --dry-run
```

---

## 🚨 Common Issues & Fixes

### Issue: Port 443 in use
```bash
sudo lsof -i :443
sudo systemctl stop apache2  # or conflicting service
```

### Issue: Permission denied
```bash
# Use Nginx reverse proxy instead of direct SSL
```

### Issue: Certificate expired
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Issue: WhatsApp webhook fails
```bash
# Ensure HTTPS is working
curl -I https://yourdomain.com/webhook

# Update webhook URL in WhatsApp settings
```

---

## 📊 Monitoring Commands

```bash
# Check certificate expiry
sudo certbot certificates

# Check Nginx status
sudo systemctl status nginx

# View SSL errors
sudo tail -f /var/log/nginx/error.log | grep ssl

# Test renewal
sudo certbot renew --dry-run

# Check SSL rating
# Visit: https://www.ssllabs.com/ssltest/
```

---

## 🔄 Renewal (Automatic)

Certbot automatically renews certificates. Verify:

```bash
# Check timer
sudo systemctl status certbot.timer

# Should show: Active: active (waiting)
```

Manual renewal (if needed):
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## 🎯 Production Checklist

- [ ] Domain pointing to server
- [ ] Cloudflare configured (optional but recommended)
- [ ] Nginx installed and configured
- [ ] SSL certificate obtained
- [ ] Auto-renewal verified
- [ ] HTTPS working (test with curl)
- [ ] WhatsApp webhook updated to HTTPS
- [ ] SSL Labs test passed (A+ rating)
- [ ] Monitoring set up
- [ ] Firewall configured (allow 80, 443)

---

## 💡 Pro Tips

1. **Always use Nginx reverse proxy** - Don't run FastAPI with direct SSL
2. **Cloudflare is your friend** - Free SSL + CDN + DDoS protection
3. **Test auto-renewal** - `sudo certbot renew --dry-run`
4. **Monitor expiry** - Set up alerts 30 days before expiry
5. **Use HSTS** - Add to Nginx config for security
6. **Block port 5000** - Only Nginx should access FastAPI

---

## 🔗 Quick Links

- **SSL Labs Test**: https://www.ssllabs.com/ssltest/
- **Certbot**: https://certbot.eff.org/
- **Cloudflare**: https://www.cloudflare.com/
- **Nginx SSL Config**: https://ssl-config.mozilla.org/

---

## 📞 Support

If SSL issues persist:
1. Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Check Certbot logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log`
3. Test certificate: `openssl s_client -connect yourdomain.com:443`
4. Verify DNS: `nslookup yourdomain.com`

---

**Your server is SSL-ready! Just add certificates and configure Nginx.** 🚀
