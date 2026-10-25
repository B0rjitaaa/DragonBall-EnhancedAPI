import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useNewVersion } from "./lib/updates";
import History from "./views/History";
import Scanner from "./views/Scanner";
import "./scan.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

const TABS = {
  scanner: { label: "Escanear", view: Scanner },
  history: { label: "Historial", view: History },
} as const;

type TabKey = keyof typeof TABS;

function currentTab(): TabKey {
  const hash = window.location.hash.slice(1);
  return hash in TABS ? (hash as TabKey) : "scanner";
}

/** /scan: identificar cartas con la cámara (del móvil o la webcam del archivador) y su historial. */
export default function ScanPage() {
  const newVersion = useNewVersion();
  const [tab, setTab] = useState<TabKey>(currentTab);

  useEffect(() => {
    const onHash = () => setTab(currentTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const View = TABS[tab].view;
  return (
    <QueryClientProvider client={queryClient}>
      <div className="scan-app">
        {newVersion && (
          <div className="update-banner" role="status">
            Hay una versión nueva de la web.
            <button onClick={() => window.location.reload()}>Recargar</button>
          </div>
        )}
        <nav className="scan-tabs" aria-label="Escáner">
          {(Object.keys(TABS) as TabKey[]).map((key) => (
            <a key={key} href={`#${key}`} className={key === tab ? "active" : ""}>
              {TABS[key].label}
            </a>
          ))}
        </nav>
        <main>
          <View />
        </main>
      </div>
    </QueryClientProvider>
  );
}
