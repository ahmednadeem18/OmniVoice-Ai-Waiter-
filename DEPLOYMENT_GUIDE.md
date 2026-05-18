# OmniVoice AI - Deployment Guide

## Prerequisites

- Python 3.11+ installed
- Node.js LTS installed
- Supabase account (free tier available)
- Git installed

## Backend Setup

### 1. Environment Configuration

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
JWT_SECRET=your-secret-key-change-in-production
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download AI Models

- Create `model_bins` directory in project root
- Download `Llama-3.2-1B-Instruct-Q4_K_M.gguf` from [Hugging Face](https://huggingface.co)
- Place in `model_bins/` directory

### 4. Run Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Visit `http://localhost:5173`

## Database Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Copy URL and API key

### 2. Initialize Database Schema

1. Go to SQL Editor in Supabase
2. Run the SQL from `backend/database_schema.sql`
3. Enable Realtime for required tables

## Production Deployment

### Backend (Heroku/Railway)

```bash
# Build container
docker build -t omnivoice-backend .

# Deploy
# (Follow platform-specific instructions)
```

### Frontend (Vercel/Netlify)

```bash
npm run build
# Upload dist/ folder
```

## Troubleshooting

### Microphone Permission Issues
- Ensure HTTPS is used in production
- Check browser permissions

### WebSocket Connection Failed
- Verify backend is running
- Check firewall settings
- Ensure CORS is enabled

### Model Loading Errors
- Check model file exists in `model_bins/`
- Verify sufficient disk space
- Check available RAM (8GB minimum recommended)

## Performance Optimization

- Use gzip compression on API responses
- Enable caching headers
- Optimize model quantization
- Use CDN for static assets

## Security Checklist

- [ ] Change JWT_SECRET in production
- [ ] Use HTTPS only
- [ ] Set strong Supabase credentials
- [ ] Enable database backups
- [ ] Set up API rate limiting
- [ ] Hash passwords properly (bcrypt)
- [ ] Validate all inputs
- [ ] Use environment variables for secrets
