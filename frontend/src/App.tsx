import AuthGate from "./components/AuthGate";
import HomePage from "./pages/HomePage";

function App() {
  return (
    <AuthGate>
      <HomePage />
    </AuthGate>
  );
}

export default App;
