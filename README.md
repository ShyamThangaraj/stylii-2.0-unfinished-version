# Stylii

An AI-powered interior design web application that transforms room photos into multiple design styles. Built with Next.js 14, TypeScript, and Tailwind CSS. Users upload room photos, set preferences, and receive photorealistic design renderings across 6 different styles (Modern, Scandinavian, Industrial, etc.) with curated product recommendations.

## 🎨 Features

- **AI-Powered Design Generation**: Transform room photos into stunning design visualizations
- **Multiple Design Styles**: Modern, Scandinavian, Industrial, Traditional, Bohemian, and more
- **Product Recommendations**: Curated Amazon product suggestions within your budget
- **Budget-Aware Shopping**: Smart product selection that respects your financial constraints
- **Video Generation**: Create design walkthrough videos (with FAL AI integration planned)
- **Voiceover Support**: AI-generated narration for design videos (ElevenLabs integration planned)
- **Responsive Design**: Beautiful, modern UI that works on all devices

## 🏗️ Architecture

### Frontend

- **Next.js 14** with TypeScript and Tailwind CSS
- **Zustand** for state management
- **shadcn/ui** components for consistent design
- **Multi-step design flow** with guided user experience

### Backend

- **FastAPI** with Python
- **Google Gemini 2.5 Flash** for AI text and image generation
- **SerpAPI** for Amazon product search and recommendations
- **Static file serving** for generated videos and images

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.8+
- Google Gemini API key
- SerpAPI key (for product recommendations)

### 1. Clone the Repository

```bash
git clone https://github.com/ShyamThangaraj/Stylii.git
cd Stylii
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

**Configure your `.env` file:**

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY_2=your_second_gemini_api_key_here
SERPAPI_KEY=your_serpapi_key_here
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install
```

### 4. Start the Development Servers

**Terminal 1 - Backend:**

```bash
cd backend
source venv/bin/activate
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📱 How to Use

1. **Upload Room Photos**: Upload 3-4 photos of your room from different angles
2. **Set Your Budget**: Choose your design budget ($500 - $20,000+)
3. **Select Design Style**: Pick from Modern, Scandinavian, Industrial, etc.
4. **Add Preferences**: Optional notes about your style preferences
5. **Generate Design**: Get AI-powered design recommendations with product suggestions
6. **View Results**: See your transformed room with curated product recommendations

## 🔧 API Endpoints

### Design Generation

- `POST /api/gemini/generate-design-queries` - Generate Amazon search queries based on room analysis
- `POST /api/nano-banana/generate-room-visualization` - Create composite room visualizations

### Video Generation

- `POST /api/video/generate-room-video` - Generate design walkthrough videos

### Health Checks

- `GET /health` - Backend health check
- `GET /api/gemini/health` - Gemini service health
- `GET /api/nano-banana/health` - Image generation health
- `GET /api/video/health` - Video generation health

## 🎯 AI Services Integration

### Google Gemini

- **Text Generation**: `gemini-2.5-flash-lite` for search query generation
- **Image Preview**: `gemini-2.5-flash-image-preview` for room visualizations
- **Image Generation**: The image generation feature uses Google's Gemini 2.5 Flash Image Preview model and requires an API key with access beyond the free tier limits for optimal performance.

### SerpAPI

- Amazon product search and recommendations
- Budget-aware product filtering
- Real-time pricing and availability

### Planned Integrations

- **FAL AI**: For advanced video generation
- **ElevenLabs**: For AI-generated voiceover narration

## 🛠️ Development

### Project Structure

```
Stylii/
├── backend/                 # FastAPI backend
│   ├── routes/             # API route handlers
│   ├── serpAPI/            # Product search integration
│   ├── image_compression/ # Image processing utilities
│   └── videogen/           # Video generation scripts
├── frontend/               # Next.js frontend
│   ├── app/                # Next.js app router pages
│   ├── components/         # React components
│   └── lib/                # Utilities and client code
└── README.md
```

### Key Technologies

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python, Google Gemini, SerpAPI
- **State Management**: Zustand
- **Styling**: Tailwind CSS with custom design system

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🚀 Deployment

### Backend Deployment

The FastAPI backend can be deployed to any Python hosting service (Railway, Render, Heroku, etc.).

### Frontend Deployment

The Next.js frontend can be deployed to Vercel, Netlify, or any static hosting service.

### Environment Variables

Make sure to set all required environment variables in your production environment:

- `GEMINI_API_KEY`
- `GEMINI_API_KEY_2`
- `SERPAPI_KEY`

---
