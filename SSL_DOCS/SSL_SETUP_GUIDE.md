# 🔒 SSL/TLS Setup Guide for Production

## Overview

This guide covers SSL/TLS certificate setup for your AI WhatsApp Backend to enable HTTPS connections in production.

---

## 📋 Why SSL/TLS is Critical

### Required For:
- ✅ **WhatsApp Webhooks** - WhatsApp requires HTTPS endpoints
- ✅ **Production Security** - Encrypts data in transit
- ✅ **API Security** - Protects sensitive data (tokens, customer info)
- ✅ **Trust & Compliance** - Industry standard for web services

### Without SSL:
- ❌ WhatsApp webhooks will fail
- ❌ Data transmitted in plain text
- ❌ Vulnerable to man-in-the-middle attacks
- ❌ Browser warnings for users

---

## 🎯 SSL Options (Choose One)

### Option 1: Let's Encrypt (Recommended - FREE)
- ✅ Free SSL certificates
- ✅ Auto-renewal
- ✅ Trusted by all browsers
- ✅ Easy setup with Certbot

### Option 2: Cloudflare (Easiest)
- ✅ Free SSL + CDN
- ✅ DDoS protection
- ✅ No server configuration needed
- ✅ Automatic certificate management

### Option 3: Nginx Reverse Proxy (Most Flexible)
- ✅ SSL termination at Nginx
- ✅ Load balancing
- ✅ Better performance
- ✅ Works with any SSL provider

### Option 4: Commercial SSL (Paid)
- ✅ Extended validation
- ✅ Wildcard certificates
- ✅ Premium support
- ⚠️ Costs $50-$300/year

---

## 🚀 Option 1: Let's Encrypt with Certbot (RECOMMENDED)

### Prerequisites
- Domain name pointing to your server
- Port 80 and 443 open
- Root/sudo access

### Step 1: Install Certbot

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx -y
```

**CentOS/RHEL:**
```bash
sudo yum install certbot python3-certbot-nginx -y
```

**Windows (WSL):**
```bash
# Use WSL Ubuntu and follow Ubuntu instructions
```

### Step 2: Stop Your Server
```bash
# Stop FastAPI server
# Press Ctrl+C in server terminal

# Or if running as service:
sudo systemctl stop ai-backend
```

### Step 3: Obtain Certificate

**Standalone Mode (No Nginx):**
```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

**With Nginx (Recommended):**
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

**Interactive Prompts:**
```
Email: your-email@example.com  (for renewal notifications)
Terms: Agree
Share email: No (optional)
```

### Step 4: Certificate Location

Certificates will be saved to:
```
Certificate: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
Private Key: /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### Step 5: Configure Environment Variables

Add to your `.env` file:
```bash
# SSL Configuration
SSL_CERTFILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEYFILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
ENVIRONMENT=production
```

### Step 6: Set Permissions

```bash
# Allow your app user to read certificates
sudo chmod 755 /etc/letsencrypt/live
sudo chmod 755 /etc/letsencrypt/archive
```

Or run server as root (not recommended):
```bash
sudo python run_server.py
```

**Better: Use Nginx reverse proxy (see Option 3)**

### Step 7: Test Certificate

```bash
# Test SSL configuration
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run
```

### Step 8: Auto-Renewal Setup

Certbot automatically creates a cron job/systemd timer. Verify:

```bash
# Check systemd timer
sudo systemctl status certbot.timer

# Or check cron
sudo crontab -l
```

Should see:
```
0 0,12 * * * certbot renew --quiet
```

### Step 9: Restart Server

```bash
python run_server.py
```

You should see:
```
🔒 SSL Enabled (Production mode)
```

---

## 🌐 Option 2: Cloudflare (Easiest Setup)

### Step 1: Add Domain to Cloudflare

1. Sign up at https://cloudflare.com
2. Add your domain
3. Update nameservers at your domain registrar

### Step 2: Enable SSL

1. Go to **SSL/TLS** tab
2. Select **Full (strict)** mode
3. Wait 5-10 minutes for activation

### Step 3: Origin Certificate (For Your Server)

1. Go to **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Download:
   - `origin-cert.pem` (certificate)
   - `origin-key.pem` (private key)

### Step 4: Install on Server

```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/cloudflare
cd /etc/ssl/cloudflare

# Upload certificates
sudo nano origin-cert.pem  # Paste certificate
sudo nano origin-key.pem   # Paste private key

# Set permissions
sudo chmod 600 origin-key.pem
sudo chmod 644 origin-cert.pem
```

### Step 5: Configure Environment

Add to `.env`:
```bash
SSL_CERTFILE=/etc/ssl/cloudflare/origin-cert.pem
SSL_KEYFILE=/etc/ssl/cloudflare/origin-key.pem
ENVIRONMENT=production
```

### Step 6: Configure Cloudflare Settings

**Recommended Settings:**
- SSL/TLS: Full (strict)
- Always Use HTTPS: On
- Automatic HTTPS Rewrites: On
- Minimum TLS Version: 1.2
- TLS 1.3: On

### Step 7: Restart Server

```bash
python run_server.py
```

**Benefits:**
- ✅ Free SSL forever
- ✅ CDN acceleration
- ✅ DDoS protection
- ✅ No renewal needed

---

## 🔧 Option 3: Nginx Reverse Proxy (BEST PRACTICE)

### Why Nginx?
- ✅ SSL termination (FastAPI runs HTTP only)
- ✅ Better performance
- ✅ Load balancing
- ✅ Static file serving
- ✅ Rate limiting

### Step 1: Install Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

### Step 2: Obtain SSL Certificate

Use Let's Encrypt (from Option 1):
```bash
sudo certbot certonly --nginx -d yourdomain.com
```

### Step 3: Configure Nginx

Create config file:
```bash
sudo nano /etc/nginx/sites-available/ai-backend
```

**Nginx Configuration:**
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (Optional but recommended)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/ai-backend-access.log;
    error_log /var/log/nginx/ai-backend-error.log;
    
    # Max upload size (for media)
    client_max_body_size 50M;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        
        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint (optional)
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
```

### Step 4: Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/ai-backend /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Step 5: Update Environment

**Remove SSL from FastAPI** (Nginx handles it):
```bash
# .env file - Remove or comment out:
# SSL_CERTFILE=...
# SSL_KEYFILE=...

ENVIRONMENT=production
```

### Step 6: Start FastAPI (HTTP Only)

```bash
python run_server.py
```

FastAPI runs on HTTP (127.0.0.1:5000), Nginx handles HTTPS.

### Step 7: Configure Firewall

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for redirect)
sudo ufw allow 80/tcp

# Block direct access to FastAPI
sudo ufw deny 5000/tcp
```

### Step 8: Test

```bash
# Test HTTPS
curl -I https://yourdomain.com/health

# Should return 200 OK
```

---

## 🔐 SSL Best Practices

### 1. Strong Cipher Suites
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers off;
```

### 2. HSTS (HTTP Strict Transport Security)
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 3. OCSP Stapling (Performance)
```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
```

### 4. Disable Old Protocols
```nginx
# Never use SSLv2, SSLv3, TLSv1, TLSv1.1
ssl_protocols TLSv1.2 TLSv1.3;
```

### 5. Certificate Pinning (Advanced)
```python
# In your app
ALLOWED_CERT_FINGERPRINTS = [
    "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
]
```

### 6. Regular Updates
```bash
# Update Certbot
sudo apt update && sudo apt upgrade certbot

# Check certificate expiry
sudo certbot certificates
```

### 7. Monitor Certificate Expiry
```bash
# Add monitoring script
#!/bin/bash
DAYS_LEFT=$(sudo certbot certificates | grep "VALID:" | awk '{print $6}')
if [ $DAYS_LEFT -lt 30 ]; then
    echo "Certificate expires in $DAYS_LEFT days!" | mail -s "SSL Alert" admin@example.com
fi
```

---

## 🧪 Testing Your SSL Setup

### 1. SSL Labs Test
Visit: https://www.ssllabs.com/ssltest/
- Enter your domain
- Should get **A** or **A+** rating

### 2. Command Line Test
```bash
# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check expiry
echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Test TLS versions
nmap --script ssl-enum-ciphers -p 443 yourdomain.com
```

### 3. Browser Test
1. Visit https://yourdomain.com
2. Click padlock icon
3. Check certificate details
4. Verify issuer and expiry

### 4. WhatsApp Webhook Test
```bash
# Test webhook endpoint
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

## 🔄 Certificate Renewal

### Automatic Renewal (Let's Encrypt)

**Certbot automatically renews certificates.** Verify:

```bash
# Check renewal timer
sudo systemctl status certbot.timer

# Manual renewal test
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal
```

### Renewal Hooks (Optional)

Create post-renewal script:
```bash
sudo nano /etc/letsencrypt/renewal-hooks/post/reload-services.sh
```

```bash
#!/bin/bash
# Reload services after renewal

# Reload Nginx
systemctl reload nginx

# Restart FastAPI (if using direct SSL)
# systemctl restart ai-backend

# Send notification
echo "SSL certificate renewed on $(date)" | mail -s "SSL Renewal" admin@example.com
```

Make executable:
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/reload-services.sh
```

---

## 🚨 Troubleshooting

### Issue 1: Certificate Not Found
```bash
# Check if certificate exists
sudo ls -la /etc/letsencrypt/live/yourdomain.com/

# Regenerate if missing
sudo certbot certonly --standalone -d yourdomain.com
```

### Issue 2: Permission Denied
```bash
# Fix permissions
sudo chmod 755 /etc/letsencrypt/live
sudo chmod 755 /etc/letsencrypt/archive

# Or use Nginx reverse proxy (recommended)
```

### Issue 3: Port 443 Already in Use
```bash
# Check what's using port 443
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # or nginx
```

### Issue 4: Certificate Expired
```bash
# Renew immediately
sudo certbot renew --force-renewal

# Restart services
sudo systemctl reload nginx
```

### Issue 5: Mixed Content Warnings
```python
# Ensure all URLs use HTTPS
WHATSAPP_GRAPH_URL = "https://graph.facebook.com/v17.0"
BACKEND_BASE_URL = "https://yourdomain.com"
```

### Issue 6: WhatsApp Webhook Fails
```bash
# Test webhook URL
curl -I https://yourdomain.com/webhook

# Check SSL certificate
openssl s_client -connect yourdomain.com:443

# Verify in WhatsApp Business API settings
```

---

## 📊 SSL Monitoring

### 1. Certificate Expiry Monitoring

**Cron Job:**
```bash
# Add to crontab
0 0 * * * /usr/local/bin/check-ssl-expiry.sh
```

**Script (`/usr/local/bin/check-ssl-expiry.sh`):**
```bash
#!/bin/bash
DOMAIN="yourdomain.com"
EXPIRY_DATE=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "SSL certificate for $DOMAIN expires in $DAYS_LEFT days!" | mail -s "SSL Alert" admin@example.com
fi
```

### 2. Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake
- CloudFlare Health Checks

### 3. Log Monitoring

```bash
# Monitor SSL errors
sudo tail -f /var/log/nginx/error.log | grep ssl

# Monitor certificate renewals
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

---

## 🎯 Recommended Setup for Your Project

### For Development (Local)
```bash
# No SSL needed
ENVIRONMENT=development
python run_server.py
```

### For Production (Recommended)
```
Internet → Cloudflare (SSL) → Nginx (Reverse Proxy) → FastAPI (HTTP)
```

**Benefits:**
- ✅ Cloudflare handles SSL + CDN + DDoS
- ✅ Nginx handles load balancing + rate limiting
- ✅ FastAPI focuses on application logic
- ✅ Easy to scale

**Setup Steps:**
1. Add domain to Cloudflare
2. Install Nginx with reverse proxy config
3. Run FastAPI on HTTP (127.0.0.1:5000)
4. Done!

---

## 📝 Quick Start Checklist

- [ ] Choose SSL option (Let's Encrypt / Cloudflare / Nginx)
- [ ] Obtain SSL certificate
- [ ] Configure environment variables
- [ ] Update WhatsApp webhook URL to HTTPS
- [ ] Test SSL with SSL Labs
- [ ] Set up auto-renewal
- [ ] Configure monitoring
- [ ] Update documentation
- [ ] Test WhatsApp webhook
- [ ] Monitor logs for SSL errors

---

## 🔗 Useful Resources

- **Let's Encrypt**: https://letsencrypt.org/
- **Certbot**: https://certbot.eff.org/
- **SSL Labs Test**: https://www.ssllabs.com/ssltest/
- **Cloudflare**: https://www.cloudflare.com/
- **Nginx SSL Config**: https://ssl-config.mozilla.org/
- **WhatsApp Webhook Docs**: https://developers.facebook.com/docs/whatsapp/

---

## 💡 Pro Tips

1. **Use Cloudflare + Nginx** for best performance and security
2. **Never commit SSL certificates** to git (add to .gitignore)
3. **Monitor certificate expiry** (set up alerts)
4. **Use HSTS** to prevent downgrade attacks
5. **Test regularly** with SSL Labs
6. **Keep Certbot updated** for security patches
7. **Use strong ciphers** (TLS 1.2+)
8. **Enable OCSP stapling** for better performance
9. **Set up log monitoring** for SSL errors
10. **Document your setup** for team members

---

**Your server already has SSL support built-in! Just add certificates and configure environment variables.** 🔒
