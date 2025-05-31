import { AuthProvider } from './contexts/AuthContext';
import AppRouter from './router';
import './App.css'

function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

export default App
