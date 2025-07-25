# Web Calibration Frontend

React-based frontend for the gaze calibration system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The application will run on http://localhost:3000

## Features

- Screen dimension detection and setup
- Camera access and preview
- 4-point calibration sequence
- Real-time frame capture and processing
- Progress tracking and completion feedback

## Tech Stack

- React with TypeScript
- Vite for build tooling
- Material-UI for components
- Axios for API calls
- React Webcam for camera access
- React Router for navigation

## API Integration

The frontend connects to the backend API running on port 8000. Key endpoints:
- POST /api/calibration/session/create
- POST /api/screen/info
- POST /api/calibration/start
- POST /api/calibration/frame
- POST /api/calibration/complete