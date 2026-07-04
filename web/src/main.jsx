import React from "react";
import { createRoot } from "react-dom/client";
import TendereAI from "../../dashboard.jsx";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <TendereAI />
  </React.StrictMode>
);
