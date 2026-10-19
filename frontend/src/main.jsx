import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@/shared/styles/index.css";
import App from "@/app/App";

async function enableMocking() {
  if (!import.meta.env.DEV || import.meta.env.VITE_USE_MOCK !== "true") return;
  const { worker } = await import("@/mocks/browser");
  await worker.start({ onUnhandledRequest: "bypass" });
}

enableMocking().then(() => {
  createRoot(document.getElementById("root")).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
});