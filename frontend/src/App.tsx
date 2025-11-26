import { AnimatePresence, motion } from "framer-motion";
import {
  CloudRain,
  Loader2,
  MapPinned,
  Send,
  Sparkles,
  ThermometerSun,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type IntentChoice = "weather" | "places" | "both";

type Place = {
  name: string;
  kind: string;
  lat: number;
  lon: number;
};

type TravelResponse = {
  message: string;
  weather?: {
    temperature_c: number;
    precip_prob_pct: number;
    observed_at: string;
  } | null;
  places?: Place[];
  vibe_tip?: string | null;
  map_url?: string | null;
  errors?: Record<string, string>;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

const timelineSteps = [
  { id: "geocode", label: "Locate Destination" },
  { id: "weather", label: "Weather Intel" },
  { id: "places", label: "Places Curator" },
  { id: "enhance", label: "Vibe & Map Magic" },
];

function App() {
  const [prompt, setPrompt] = useState("Plan a Bangalore escape");
  const [intent, setIntent] = useState<IntentChoice>("both");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<TravelResponse | null>(null);
  const [activePulse, setActivePulse] = useState(0);

  useEffect(() => {
    if (!loading) return;
    setActivePulse(0);
    const interval = setInterval(() => {
      setActivePulse((prev) => (prev + 1) % timelineSteps.length);
    }, 900);
    return () => clearInterval(interval);
  }, [loading]);

  const completedSteps = useMemo(() => {
    const completed = new Set<string>();
    if (!response) return completed;
    completed.add("geocode");
    if (response.weather || response.errors?.weather) {
      completed.add("weather");
    }
    if ((response.places?.length ?? 0) > 0 || response.errors?.places) {
      completed.add("places");
    }
    if (response.vibe_tip || response.map_url) {
      completed.add("enhance");
    }
    return completed;
  }, [response]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await fetchTravelPlan(prompt.trim(), intent);
      setResponse(data);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while calling the parent agent.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#020114]">
      <BackgroundGlow />
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-12 md:px-10">
        <header className="text-center">
          <p className="font-display text-sm uppercase tracking-[0.5em] text-indigo-300">
            Multi-Agent Tourism Orchestrator
          </p>
          <h1 className="mt-6 font-display text-4xl leading-tight text-white sm:text-5xl lg:text-6xl">
            Travel intel, vibes, and visuals powered by{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-cyan-200 bg-clip-text text-transparent">
              LangGraph + MCP
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
            The Parent Agent routes your request to Weather & Places specialists,
            then layers on packing vibes and a live map so you can feel the trip
            before you book it.
          </p>
        </header>

        <section className="mt-10 space-y-8">
          <PlannerForm
            prompt={prompt}
            setPrompt={setPrompt}
            intent={intent}
            setIntent={setIntent}
            loading={loading}
            onSubmit={handleSubmit}
          />

          <Timeline
            activePulse={loading ? activePulse : -1}
            completed={completedSteps}
            loading={loading}
          />

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="rounded-2xl border border-red-500/40 bg-red-500/10 px-6 py-4 text-sm text-red-200 shadow-glass"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {response ? (
            <ResponseDeck response={response} />
          ) : (
            <Placeholder />
          )}
        </section>
      </div>
    </div>
  );
}

function PlannerForm({
  prompt,
  setPrompt,
  intent,
  setIntent,
  loading,
  onSubmit,
}: {
  prompt: string;
  setPrompt: (v: string) => void;
  intent: IntentChoice;
  setIntent: (v: IntentChoice) => void;
  loading: boolean;
  onSubmit: (event: React.FormEvent) => void;
}) {
  const intents: { label: string; value: IntentChoice; caption: string }[] = [
    { label: "Weather", value: "weather", caption: "Temperature & rain" },
    { label: "Places", value: "places", caption: "Top 5 attractions" },
    { label: "Everything", value: "both", caption: "Weather + places" },
  ];

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-glass backdrop-blur-3xl"
    >
      <div className="flex flex-wrap gap-3">
        {intents.map((option) => {
          const isSelected = option.value === intent;
          return (
            <button
              type="button"
              key={option.value}
              onClick={() => setIntent(option.value)}
              className={`flex flex-col rounded-2xl border px-4 py-3 text-left transition
                ${
                  isSelected
                    ? "border-indigo-400 bg-indigo-500/10 text-white"
                    : "border-white/10 bg-white/5 text-slate-300 hover:border-white/40"
                }`}
            >
              <span className="font-semibold">{option.label}</span>
              <span className="text-xs text-slate-400">{option.caption}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-6 flex flex-col gap-4 md:flex-row">
        <div className="flex-1">
          <label className="text-sm uppercase tracking-[0.2em] text-slate-400">
            Your Travel Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
            className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-base text-white outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-300/50"
            placeholder="e.g., Weather and hidden gems around Kyoto next weekend"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="flex items-center justify-center rounded-2xl bg-gradient-to-r from-indigo-500 via-sky-400 to-cyan-300 px-8 py-4 text-lg font-semibold text-slate-950 shadow-lg shadow-indigo-500/40 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <>
              Launch Plan
              <Send className="ml-2 h-5 w-5" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}

function Timeline({
  completed,
  loading,
  activePulse,
}: {
  completed: Set<string>;
  loading: boolean;
  activePulse: number;
}) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/30 p-6 backdrop-blur-3xl">
      <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
        Parent Agent Flow
      </p>
      <div className="mt-4 grid gap-4 md:grid-cols-4">
        {timelineSteps.map((step, index) => {
          const isDone = completed.has(step.id);
          const isActive = loading && index === activePulse;
          return (
            <div
              key={step.id}
              className={`rounded-2xl border px-4 py-5 transition ${
                isDone
                  ? "border-emerald-400/60 bg-emerald-400/10 text-emerald-200"
                  : isActive
                    ? "border-indigo-400/60 bg-indigo-500/10 text-indigo-100"
                    : "border-white/10 bg-white/5 text-slate-300"
              }`}
            >
              <p className="text-sm font-semibold">{step.label}</p>
              <p className="mt-2 text-xs text-slate-400">
                {isDone
                  ? "Complete"
                  : isActive
                    ? "Running..."
                    : "Queued"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResponseDeck({ response }: { response: TravelResponse }) {
  const hasWeather = Boolean(response.weather);
  const hasPlaces = Boolean(response.places && response.places.length > 0);
  const hasVibe = Boolean(response.vibe_tip);
  const hasMap = Boolean(response.map_url);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr,0.8fr]">
      <div className="space-y-6">
        <motion.div
          layout
          className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-glass"
        >
          <p className="text-sm uppercase tracking-[0.3em] text-slate-400">
            Parent Agent Summary
          </p>
          <p className="mt-3 text-lg text-white">{response.message}</p>
          {response.errors && Object.keys(response.errors).length > 0 && (
            <div className="mt-4 rounded-2xl border border-amber-400/40 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
              <p className="mb-2 font-semibold text-amber-100">⚠️ Partial Results</p>
              {Object.entries(response.errors).map(([key, value]) => (
                <p key={key} className="mt-1">
                  <span className="font-medium capitalize">{key}:</span>{" "}
                  {formatErrorMessage(value)}
                </p>
              ))}
            </div>
          )}
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2">
          {hasWeather && (
            <motion.div
              layout
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-3xl border border-indigo-400/40 bg-indigo-500/10 p-6"
            >
              <div className="flex items-center gap-3 text-indigo-200">
                <ThermometerSun className="h-6 w-6" />
                <span className="text-sm uppercase tracking-[0.3em]">
                  Weather
                </span>
              </div>
              <p className="mt-4 text-5xl font-semibold text-white">
                {response.weather?.temperature_c?.toFixed(0)}°C
              </p>
              <p className="mt-2 text-sm text-indigo-100">
                Precipitation chance: {response.weather?.precip_prob_pct}%
              </p>
              <p className="mt-1 text-xs text-indigo-200/70">
                Observed {new Date(response.weather?.observed_at ?? "").toUTCString()}
              </p>
            </motion.div>
          )}

          {hasPlaces && (
            <motion.div
              layout
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-3xl border border-slate-200/10 bg-slate-900/60 p-6"
            >
              <div className="flex items-center gap-3 text-slate-200">
                <MapPinned className="h-6 w-6" />
                <span className="text-sm uppercase tracking-[0.3em]">
                  Places
                </span>
              </div>
              <div className="mt-4 space-y-3 text-sm text-slate-200">
                {response.places?.slice(0, 5).map((place) => (
                  <div
                    key={place.name}
                    className="rounded-2xl border border-white/5 bg-white/5 px-4 py-3"
                  >
                    <p className="font-semibold text-white">{place.name}</p>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                      {place.kind}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {hasVibe && (
          <motion.div
            layout
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="rounded-3xl border border-emerald-400/40 bg-emerald-400/10 p-6 text-emerald-50"
          >
            <div className="flex items-center gap-3">
              <Sparkles className="h-6 w-6" />
              <span className="text-sm uppercase tracking-[0.3em]">
                Vibe Match
              </span>
            </div>
            <p className="mt-4 text-base text-white">
              {response.vibe_tip}
            </p>
          </motion.div>
        )}

        {hasMap && (
          <motion.div
            layout
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="rounded-3xl border border-cyan-300/40 bg-cyan-400/5 p-4"
          >
            <p className="px-2 text-xs uppercase tracking-[0.4em] text-cyan-200">
              Route Visualization
            </p>
            <div className="mt-3 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/50">
              <MapDisplay mapUrl={response.map_url ?? ""} places={response.places ?? []} />
            </div>
            {response.places && response.places.length > 0 && (
              <a
                href={`https://www.openstreetmap.org/?mlat=${response.places[0].lat}&mlon=${response.places[0].lon}&zoom=12`}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center text-sm font-semibold text-cyan-200 hover:text-cyan-100 transition"
              >
                Open in OpenStreetMap →
              </a>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}

function Placeholder() {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-10 text-center text-slate-400">
      <CloudRain className="mx-auto h-12 w-12 text-slate-500" />
      <p className="mt-4 text-lg text-slate-300">
        Your personalized travel briefing will land here.
      </p>
      <p className="text-sm text-slate-400">
        Ask for weather, places, or both—then watch the agents collaborate in
        real time.
      </p>
    </div>
  );
}

function BackgroundGlow() {
  return (
    <>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(79,70,229,0.35),_transparent_55%)]" />
      <div className="pointer-events-none absolute inset-y-0 left-1/2 w-[40rem] -translate-x-1/2 rotate-45 bg-gradient-to-b from-sky-500/30 via-transparent to-transparent blur-3xl" />
    </>
  );
}

function formatErrorMessage(error: string): string {
  // Make error messages more user-friendly
  if (error.includes("Overpass API may be temporarily unavailable")) {
    return "The places service is temporarily unavailable. Please try again in a moment.";
  }
  if (error.includes("Gateway timeout") || error.includes("504")) {
    return "The service took too long to respond. Please try again.";
  }
  if (error.includes("Timeout")) {
    return "Request timed out. Please try again.";
  }
  // Return original error if no specific formatting needed
  return error;
}

function MapDisplay({ mapUrl, places }: { mapUrl: string; places: Place[] }) {
  const [useIframe, setUseIframe] = useState(false);

  // Build iframe embed URL from places if image fails
  const buildIframeUrl = () => {
    if (places.length < 2) return null;
    const lats = places.map((p) => p.lat);
    const lons = places.map((p) => p.lon);
    const bbox = `${Math.min(...lons)},${Math.min(...lats)},${Math.max(...lons)},${Math.max(...lats)}`;
    return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${places[0].lat},${places[0].lon}`;
  };

  const iframeUrl = buildIframeUrl();

  if (useIframe && iframeUrl) {
    return (
      <iframe
        src={iframeUrl}
        className="h-64 w-full border-0"
        title="Route map"
        loading="lazy"
      />
    );
  }

  return (
    <img
      src={mapUrl}
      alt="Route map"
      className="h-64 w-full object-cover"
      onError={() => {
        if (iframeUrl) {
          setUseIframe(true);
        }
      }}
    />
  );
}

async function fetchTravelPlan(prompt: string, intent: IntentChoice) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 900));
    return buildMockResponse(intent);
  }

  const response = await fetch(`${API_URL}/travel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, intent }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

function buildMockResponse(intent: IntentChoice): TravelResponse {
  const basePlaces: Place[] = [
    { name: "Bangalore Palace", kind: "palace", lat: 12.998, lon: 77.592 },
    { name: "Lalbagh Botanical Garden", kind: "garden", lat: 12.95, lon: 77.584 },
    { name: "Cubbon Park", kind: "park", lat: 12.976, lon: 77.592 },
    { name: "National Gallery of Modern Art", kind: "museum", lat: 12.998, lon: 77.58 },
    { name: "Bannerghatta National Park", kind: "wildlife", lat: 12.8, lon: 77.57 },
  ];

  const payload: TravelResponse = {
    message:
      "Here's what I found for Bengaluru: warm afternoons with a slight chance of showers plus five standout experiences.",
    weather:
      intent !== "places"
        ? {
            temperature_c: 25,
            precip_prob_pct: 35,
            observed_at: new Date().toISOString(),
          }
        : null,
    places: intent !== "weather" ? basePlaces : [],
    vibe_tip:
      intent === "weather"
        ? "Tip: Light breathable layers with a compact umbrella keep you ready for tropical swings."
        : "Tip: Outdoor-forward plan with possible showers—pack a light raincoat and city-walk sneakers.",
    map_url:
      intent === "weather"
        ? null
        : "https://staticmap.openstreetmap.de/staticmap.php?center=12.97,77.59&zoom=12&size=600x400&markers=12.998,77.592,red-1|12.95,77.584,red-2|12.976,77.592,red-3|12.998,77.58,red-4|12.8,77.57,red-5",
  };

  if (intent === "weather") {
    payload.places = [];
  }

  return payload;
}

export default App;
