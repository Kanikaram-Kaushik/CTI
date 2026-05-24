import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

// Move head/meta/font tags into React runtime so index.html can be minimal.
const ensureHead = () => {
  if (document.head.__cti_injected) return;
  document.title = "CTI RAG Assistant";

  const metaCharset = document.createElement("meta");
  metaCharset.setAttribute("charset", "UTF-8");
  document.head.appendChild(metaCharset);

  const metaViewport = document.createElement("meta");
  metaViewport.name = "viewport";
  metaViewport.content = "width=device-width, initial-scale=1.0";
  document.head.appendChild(metaViewport);

  const pre1 = document.createElement("link");
  pre1.rel = "preconnect";
  pre1.href = "https://fonts.googleapis.com";
  document.head.appendChild(pre1);

  const pre2 = document.createElement("link");
  pre2.rel = "preconnect";
  pre2.href = "https://fonts.gstatic.com";
  pre2.crossOrigin = "";
  document.head.appendChild(pre2);

  const fontLink = document.createElement("link");
  fontLink.rel = "stylesheet";
  fontLink.href =
    "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap";
  document.head.appendChild(fontLink);

  document.head.__cti_injected = true;
};

ensureHead();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
