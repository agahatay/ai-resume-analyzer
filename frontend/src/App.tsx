import AuthGate from "./components/AuthGate";
import { AuthProvider } from "./context/AuthContext";
import HomePage from "./pages/HomePage";

function App() {
  return (
    <AuthProvider>
      <AuthGate>
        <HomePage />
      </AuthGate>
    </AuthProvider>
  );
}

export default App;
