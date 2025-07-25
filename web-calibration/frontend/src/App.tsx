import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import CalibrationPage from './pages/CalibrationPage';
import PreCheckPage from './pages/PreCheckPage';
import CompletionPage from './pages/CompletionPage';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<PreCheckPage />} />
          <Route path="/calibration" element={<CalibrationPage />} />
          <Route path="/completion" element={<CompletionPage />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;