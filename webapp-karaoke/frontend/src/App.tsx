import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { JobPage } from './pages/JobPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/j/:jobId" element={<JobPage />} />
      </Routes>
    </BrowserRouter>
  );
}
