# Reel Studio – Frontend

React + TypeScript frontend for the Reel Studio AI video platform.

## Tech Stack

- React 18
- TypeScript
- Tailwind CSS
- React Router
- Axios
- React Player
- Lucide Icons

## Getting Started

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start the development server

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

### 3. Backend

Make sure the backend (see ../README.md) is running at `http://localhost:8000`.

You can change the API URL by creating a `.env` file:

```
REACT_APP_API_URL=http://localhost:8000/api
```

## Pages

| Route              | Description                              |
|--------------------|------------------------------------------|
| `/`                | Landing page                             |
| `/upload`          | Upload class recordings                  |
| `/dashboard`       | List of all videos + status              |
| `/editor/:videoId` | Workspace: video explained, reel studio, live captions, transcript |
| `/explainer`       | Generate topic-based explainer videos    |

## Project Structure

```
src/
├── components/       # Reusable UI components
├── pages/            # Route pages
├── services/         # API calls
├── types/            # TypeScript interfaces
└── utils/            # Helper functions
```

## Notes

- The frontend polls the backend every few seconds while a video is processing.
- All API calls are centralized in `src/services/api.ts`.
- Styling is done with Tailwind CSS.
