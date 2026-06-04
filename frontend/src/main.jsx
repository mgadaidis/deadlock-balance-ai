import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { ItemsProvider } from './contexts/ItemsContext.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* ItemsProvider is mounted at the root so every page reads items the
          same way via useItems(). */}
      <ItemsProvider>
        <App />
      </ItemsProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
