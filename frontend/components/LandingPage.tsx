"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const NAV_LINKS = [
  { label: "Features",     id: "features"     },
  { label: "How it works", id: "how-it-works" },
  { label: "For Clinics",  id: "for-clinics"  },
];

function scrollTo(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ─── Nav ───────────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-slate-900/95 backdrop-blur-sm border-b border-slate-700/60 shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2 shrink-0 group">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 1 L23 23 L1 23 Z M12 6 L19 23 L5 23 Z M5 15 L19 15 L19 18 L5 18 Z"
              fill="#2dd4bf"
            />
          </svg>
          <span className="text-[17px] font-semibold text-white tracking-tight group-hover:text-teal-100 transition-colors">
            Arlo
          </span>
        </a>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ label, id }) => (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              className="px-3.5 py-2 text-sm rounded-md transition-colors text-slate-300 hover:text-white hover:bg-white/10"
            >
              {label}
            </button>
          ))}
        </nav>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm px-4 py-2 rounded-md transition-colors text-slate-300 hover:text-white"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="text-sm px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium transition-all shadow-sm hover:shadow-teal-500/25 hover:shadow-md"
          >
            Get started
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <div className="space-y-1.5">
            <span className="block w-5 h-0.5 bg-slate-300" />
            <span className={`block w-5 h-0.5 bg-slate-300 transition-opacity ${menuOpen ? "opacity-0" : ""}`} />
            <span className="block w-5 h-0.5 bg-slate-300" />
          </div>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-slate-900/95 backdrop-blur-sm border-b border-slate-700 px-6 py-4 space-y-2">
          {NAV_LINKS.map(({ label, id }) => (
            <button
              key={id}
              onClick={() => { scrollTo(id); setMenuOpen(false); }}
              className="block w-full text-left py-2 text-sm text-slate-300 hover:text-teal-400 transition-colors"
            >
              {label}
            </button>
          ))}
          <div className="pt-2 flex flex-col gap-2">
            <Link href="/login" className="text-sm text-center py-2.5 border border-slate-600 rounded-lg text-slate-300 hover:border-slate-500 hover:text-white transition-colors">
              Log in
            </Link>
            <Link href="/register" className="text-sm text-center py-2.5 bg-teal-600 hover:bg-teal-700 rounded-lg text-white font-medium transition-colors">
              Get started free
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

// ─── Hero ──────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="relative min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 overflow-hidden flex items-center">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.15) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-teal-500/20 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-0 w-80 h-80 bg-teal-400/10 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-6 py-24 grid lg:grid-cols-2 gap-16 items-center">
        {/* Left – copy */}
        <div className="animate-slide-in">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-400 text-xs font-medium mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse2" />
            Now in beta — free for licensed vets
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-[1.1] tracking-tight mb-6">
            Clinical intelligence{" "}
            <span className="bg-gradient-to-r from-teal-400 to-teal-400 bg-clip-text text-transparent">
              built for vets
            </span>
          </h1>

          <p className="text-lg text-slate-400 leading-relaxed mb-10 max-w-lg">
            Evidence-based answers to your toughest clinical questions — drug dosages,
            differential diagnoses, treatment protocols — instantly, at the point of care.
          </p>

          <div className="flex flex-wrap gap-4">
            <Link
              href="/register"
              className="px-6 py-3.5 bg-teal-600 hover:bg-teal-500 text-white font-semibold rounded-xl transition-all shadow-lg hover:shadow-teal-500/25 hover:-translate-y-0.5"
            >
              Start for free
            </Link>
            <a
              href="#how-it-works"
              className="px-6 py-3.5 bg-white/5 hover:bg-white/10 text-white font-medium rounded-xl border border-white/10 hover:border-white/20 transition-all"
            >
              See how it works →
            </a>
          </div>

          <p className="mt-6 text-xs text-slate-500">
            No credit card required · GDPR compliant · Used by 500+ veterinary professionals
          </p>
        </div>

        {/* Right – Chat mockup */}
        <div className="animate-float hidden lg:block">
          <ChatMockup />
        </div>
      </div>

      {/* Bottom fade — dark to dark, no white bleed */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-slate-950 to-transparent" />
    </section>
  );
}

function ChatMockup() {
  const messages = [
    {
      role: "user",
      text: "What's the safe ketamine dose for a 4kg cat under GA?",
    },
    {
      role: "assistant",
      text: "For feline patients, ketamine is typically dosed at 2–4 mg/kg IV when used as part of a balanced anesthetic protocol. At 4 kg, that's 8–16 mg IV. Combine with a benzodiazepine (e.g. midazolam 0.2 mg/kg) to reduce muscle rigidity and recovery excitement.",
      sources: ["Plumb's Veterinary Drugs", "BSAVA Manual of Anaesthesia"],
    },
    {
      role: "user",
      text: "Any contraindications to watch for?",
    },
  ];

  return (
    <div className="relative bg-slate-800/80 backdrop-blur border border-slate-700/50 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden max-w-md ml-auto">
      {/* Titlebar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-700/50 bg-slate-900/50">
        <div className="w-3 h-3 rounded-full bg-red-500/70" />
        <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
        <div className="w-3 h-3 rounded-full bg-green-500/70" />
        <div className="ml-3 flex items-center gap-1.5">
          <span className="text-white text-xs">🐾</span>
          <span className="text-slate-400 text-xs font-medium">Arlo</span>
        </div>
      </div>

      {/* Messages */}
      <div className="px-4 py-4 space-y-4 text-sm">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-teal-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs">🐾</span>
              </div>
            )}
            <div className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 ${
              msg.role === "user"
                ? "bg-teal-600 text-white rounded-br-sm"
                : "bg-slate-700/60 text-slate-200 rounded-bl-sm"
            }`}>
              <p className="leading-relaxed">{msg.text}</p>
              {msg.sources && (
                <div className="mt-2 pt-2 border-t border-slate-600/50 space-y-0.5">
                  {msg.sources.map((s) => (
                    <p key={s} className="text-[11px] text-teal-400 flex items-center gap-1">
                      <span>📖</span> {s}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        <div className="flex gap-2.5 items-center">
          <div className="w-7 h-7 rounded-full bg-teal-600 flex items-center justify-center flex-shrink-0">
            <span className="text-xs">🐾</span>
          </div>
          <div className="bg-slate-700/60 rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5 items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "120ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "240ms" }} />
          </div>
        </div>
      </div>

      {/* Input bar */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2 bg-slate-700/50 border border-slate-600/50 rounded-xl px-3.5 py-2.5">
          <span className="text-slate-500 text-xs flex-1">Ask a clinical question…</span>
          <button className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center flex-shrink-0">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Features ──────────────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: "🔬",
    title: "Instant Clinical Answers",
    description:
      "Ask any clinical question and receive evidence-based responses grounded in peer-reviewed literature, pharmacology references, and specialist guidelines — in seconds.",
    tag: "AI-powered",
  },
  {
    icon: "💊",
    title: "Drug & Treatment Reference",
    description:
      "Access accurate drug dosages, contraindications, and drug interaction data for hundreds of companion and exotic species without leaving the consultation room.",
    tag: "500+ species",
  },
  {
    icon: "🚨",
    title: "Emergency Protocols",
    description:
      "Step-by-step emergency triage and treatment protocols for critical patients — from CPR guidelines to toxin management — available when every second counts.",
    tag: "24/7 available",
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-teal-400 tracking-widest uppercase mb-3">
            What Arlo does
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
            Everything a vet needs,<br className="hidden sm:block" /> right at the point of care
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Built specifically for veterinary professionals — not a general-purpose chatbot repurposed for medicine.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group p-8 rounded-2xl border border-slate-700 bg-slate-800/50 hover:border-teal-500/40 hover:shadow-xl hover:shadow-teal-900/20 transition-all duration-300 hover:-translate-y-1"
            >
              <div className="w-12 h-12 rounded-xl bg-teal-900/30 flex items-center justify-center text-2xl mb-5 group-hover:bg-teal-900/50 transition-colors">
                {f.icon}
              </div>
              <div className="inline-block px-2.5 py-0.5 rounded-full bg-teal-900/30 text-teal-400 text-xs font-medium mb-3">
                {f.tag}
              </div>
              <h3 className="text-lg font-semibold text-white mb-3">{f.title}</h3>
              <p className="text-slate-400 leading-relaxed text-sm">{f.description}</p>
              <div className="mt-5 text-teal-400 text-sm font-medium group-hover:text-teal-300 flex items-center gap-1.5">
                Learn more <span className="group-hover:translate-x-0.5 transition-transform inline-block">→</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Clinical Examples ─────────────────────────────────────────────────────────
const EXAMPLES = [
  {
    label: "Drug Dosage",
    icon: "💊",
    question: "What's the safe meloxicam dose for a 10 kg dog with osteoarthritis?",
    answer: [
      { type: "text", content: "For a 10 kg dog, the initial meloxicam dose is:" },
      {
        type: "table",
        rows: [
          ["Day 1 (loading)", "0.2 mg/kg", "2.0 mg", "Once daily with food"],
          ["Maintenance", "0.1 mg/kg", "1.0 mg", "Once daily with food"],
        ],
        headers: ["Phase", "Dose", "Amount", "Administration"],
      },
      {
        type: "warning",
        content:
          "Monitor renal function before starting and after 14 days. Avoid in patients with GI disease, renal insufficiency, or concurrent NSAID use.",
      },
    ],
    sources: ["Plumb's Veterinary Drug Handbook, 10th Ed.", "BSAVA Small Animal Formulary"],
  },
  {
    label: "Emergency",
    icon: "🚨",
    question: "Dog ingested xylitol gum (~3 pieces) 20 min ago. Steps?",
    answer: [
      { type: "text", content: "Xylitol toxicity — act immediately. Estimated dose: ~0.3 g/kg (hepatotoxic range >0.5 g/kg)." },
      {
        type: "steps",
        items: [
          "Induce emesis if < 30 min post-ingestion and patient is alert (apomorphine 0.03 mg/kg IV or IM).",
          "Establish IV access — start dextrose supplementation (2.5–5% dextrose in 0.9% NaCl).",
          "Check baseline glucose, ALT, ALP, and bilirubin immediately.",
          "Monitor BGL every 30–60 min for 12 hours minimum.",
          "If ALT elevation detected at 24 h, begin hepatoprotective support (SAMe, NAC).",
          "Hospitalise for 24–72 h monitoring depending on dose ingested.",
        ],
      },
    ],
    sources: ["ASPCA Animal Poison Control Center", "Merck Veterinary Manual — Xylitol Toxicosis"],
  },
  {
    label: "Differential Diagnosis",
    icon: "🔬",
    question: "5-year-old cat, PU/PD, weight loss, polyphagia. Top differentials?",
    answer: [
      { type: "text", content: "Classic PU/PD triad in a middle-aged cat. Ranked differentials by probability:" },
      {
        type: "differentials",
        items: [
          { rank: 1, condition: "Hyperthyroidism", probability: "High", note: "Check T4; weight loss + polyphagia is classic" },
          { rank: 2, condition: "Diabetes mellitus", probability: "High", note: "Fasting glucose + fructosamine; check for glucosuria" },
          { rank: 3, condition: "Chronic kidney disease", probability: "Moderate", note: "SDMA, creatinine, UA — often concurrent with hyperthyroidism" },
          { rank: 4, condition: "Hepatic disease", probability: "Lower", note: "ALT, ALP, bile acids, abdominal ultrasound" },
        ],
      },
      { type: "text", content: "Recommend: T4, glucose, BMP, UA with culture, and abdominal ultrasound as first-line workup." },
    ],
    sources: ["Ettinger & Feldman: Textbook of Veterinary Internal Medicine", "ISFM Feline Hyperthyroidism Guidelines"],
  },
];

function ExamplesSection() {
  const [active, setActive] = useState(0);
  const ex = EXAMPLES[active];

  return (
    <section className="py-24 bg-slate-900">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-teal-400 tracking-widest uppercase mb-3">
            See it in action
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
            Real clinical questions,<br className="hidden sm:block" /> real answers
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto text-sm">
            Ask anything you&apos;d look up in a textbook — get a structured, cited answer in seconds.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-8 flex-wrap">
          {EXAMPLES.map((e, i) => (
            <button
              key={e.label}
              onClick={() => setActive(i)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                active === i
                  ? "bg-teal-600 text-white shadow-lg shadow-teal-900/40"
                  : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white border border-white/10"
              }`}
            >
              <span>{e.icon}</span> {e.label}
            </button>
          ))}
        </div>

        {/* Chat window */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
          {/* Titlebar */}
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-700/50 bg-slate-900/60">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <div className="w-3 h-3 rounded-full bg-green-500/60" />
            </div>
            <div className="ml-3 flex items-center gap-2 text-slate-400 text-xs">
              <span>🐾</span>
              <span>Arlo — Clinical Query</span>
            </div>
          </div>

          <div className="p-6 space-y-5">
            {/* User message */}
            <div className="flex justify-end">
              <div className="max-w-2xl bg-teal-600 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed">
                {ex.question}
              </div>
            </div>

            {/* AI response */}
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md">
                <span className="text-sm">🐾</span>
              </div>
              <div className="flex-1 space-y-3">
                {ex.answer.map((block, i) => {
                  if (block.type === "text") {
                    return (
                      <p key={i} className="text-slate-200 text-sm leading-relaxed">{block.content as string}</p>
                    );
                  }
                  if (block.type === "table") {
                    const t = block as typeof block & { headers: string[]; rows: string[][] };
                    return (
                      <div key={i} className="overflow-x-auto rounded-xl border border-slate-700/50">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-slate-900/60">
                              {t.headers.map((h) => (
                                <th key={h} className="px-4 py-2.5 text-left text-slate-400 font-semibold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {t.rows.map((row, ri) => (
                              <tr key={ri} className="border-t border-slate-700/40 hover:bg-slate-700/20 transition-colors">
                                {row.map((cell, ci) => (
                                  <td key={ci} className={`px-4 py-2.5 ${ci === 0 ? "text-teal-400 font-medium" : "text-slate-300"}`}>{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  }
                  if (block.type === "warning") {
                    return (
                      <div key={i} className="flex gap-2.5 bg-teal-500/10 border border-teal-500/20 rounded-xl px-4 py-3">
                        <span className="text-teal-400 text-sm flex-shrink-0">⚠️</span>
                        <p className="text-teal-200/90 text-xs leading-relaxed">{block.content as string}</p>
                      </div>
                    );
                  }
                  if (block.type === "steps") {
                    const s = block as typeof block & { items: string[] };
                    return (
                      <ol key={i} className="space-y-2">
                        {s.items.map((item, si) => (
                          <li key={si} className="flex gap-3 items-start text-sm text-slate-300">
                            <span className="w-5 h-5 rounded-full bg-teal-600/30 border border-teal-500/40 text-teal-400 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{si + 1}</span>
                            <span className="leading-relaxed">{item}</span>
                          </li>
                        ))}
                      </ol>
                    );
                  }
                  if (block.type === "differentials") {
                    const d = block as typeof block & { items: { rank: number; condition: string; probability: string; note: string }[] };
                    return (
                      <div key={i} className="space-y-2">
                        {d.items.map((item) => (
                          <div key={item.rank} className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/40 border border-slate-700/40">
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5 ${
                              item.probability === "High" ? "bg-teal-600/30 text-teal-400 border border-teal-500/30" :
                              item.probability === "Moderate" ? "bg-blue-600/20 text-blue-400 border border-blue-500/20" :
                              "bg-slate-700/50 text-slate-400 border border-slate-600/30"
                            }`}>{item.probability}</span>
                            <div>
                              <p className="text-sm font-semibold text-slate-100">{item.condition}</p>
                              <p className="text-xs text-slate-400 mt-0.5">{item.note}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                })}

                {/* Sources */}
                <div className="pt-2 border-t border-slate-700/40 flex flex-wrap gap-2">
                  {ex.sources.map((s) => (
                    <span key={s} className="inline-flex items-center gap-1.5 text-xs text-teal-400 bg-teal-900/30 border border-teal-800/40 rounded-lg px-2.5 py-1">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-500 mt-5">
          Answers are sourced from peer-reviewed veterinary research, academic papers, and scientific journals. Independent expert review is recommended before applying findings in clinical practice.
        </p>
      </div>
    </section>
  );
}

// ─── Clinical Algorithms Section ──────────────────────────────────────────────
type FlowStep =
  | { type: "node"; text: string; sub?: string; highlight?: boolean }
  | { type: "branch"; items: string[] }
  | { type: "note"; text: string };

const ALGORITHMS: {
  title: string;
  icon: string;
  query: string;
  steps: FlowStep[];
  source: string;
  time: string;
}[] = [
  {
    title: "Vomiting Workup",
    icon: "🤢",
    query: "Diagnostic approach for vomiting in dogs and cats",
    steps: [
      { type: "node", text: "Vomiting", highlight: true },
      { type: "node", text: "History / physical examination" },
      { type: "branch", items: ["Acute", "Chronic", "Hematemesis"] },
      { type: "note", text: "Mild → supportive care first" },
      { type: "node", text: "CBC · chemistry · urinalysis", sub: "thyroxine, FeLV/FIV (cats) · cPLI, cortisol (dogs) · abdominal imaging" },
      { type: "note", text: "If inconclusive →" },
      { type: "node", text: "Fasting bile acids · serum gastrin" },
      { type: "node", text: "Gastroduodenoscopy + biopsy" },
      { type: "node", text: "CSF tap · CT · MRI" },
    ],
    source: "Ettinger & Feldman — TVIM, 8th Ed. Fig. 26.2",
    time: "3.8s",
  },
  {
    title: "Respiratory Distress",
    icon: "🫁",
    query: "Emergency approach to dyspnea in companion animals",
    steps: [
      { type: "node", text: "Respiratory distress", highlight: true },
      { type: "node", text: "O₂ supplementation + minimal handling" },
      { type: "node", text: "Rapid physical assessment" },
      { type: "branch", items: ["Upper airway", "Parenchymal", "Pleural space"] },
      { type: "node", text: "Thoracic radiograph · point-of-care ultrasound" },
      { type: "note", text: "Pleural effusion → thoracocentesis first" },
      { type: "node", text: "Targeted treatment", sub: "Furosemide · bronchodilators · thoracocentesis · intubation" },
      { type: "node", text: "Monitor SpO₂ · RR · effort · ABG" },
      { type: "node", text: "Advanced imaging / bronchoscopy if unresolved" },
    ],
    source: "BSAVA Manual of Canine & Feline Emergency & Critical Care",
    time: "4.1s",
  },
  {
    title: "Shock Protocol",
    icon: "💔",
    query: "Recognition and management of shock in small animals",
    steps: [
      { type: "node", text: "Acute collapse / suspected shock", highlight: true },
      { type: "node", text: "Assess: HR · MM color · CRT · BP · mentation" },
      { type: "branch", items: ["Hypovolemic", "Distributive", "Cardiogenic"] },
      { type: "note", text: "Cardiogenic: echo before IV fluids" },
      { type: "node", text: "IV access · fluid resuscitation", sub: "Isotonic crystalloid 20 mL/kg bolus IV · reassess every 15 min" },
      { type: "node", text: "Identify & treat underlying cause" },
      { type: "node", text: "Vasopressors if refractory", sub: "Norepinephrine 0.1–1 µg/kg/min · dopamine 5–20 µg/kg/min" },
      { type: "node", text: "Monitor: lactate · MAP · urine output · SpO₂" },
      { type: "node", text: "Blood products if PCV < 20% or TP < 35 g/L" },
    ],
    source: "Silverstein & Hopper — Small Animal Critical Care Medicine",
    time: "5.2s",
  },
];

function Arrow() {
  return (
    <div className="flex flex-col items-center my-0.5">
      <div className="w-px h-3 bg-teal-500/50" />
      <svg width="10" height="6" viewBox="0 0 10 6">
        <polygon points="0,0 10,0 5,6" fill="#14b8a6" opacity="0.7" />
      </svg>
    </div>
  );
}

function AlgoCard({ algo }: { algo: typeof ALGORITHMS[0] }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/40 rounded-2xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700/40 bg-slate-900/50">
        <div className="flex items-center gap-2.5 mb-1.5">
          <span className="text-lg">{algo.icon}</span>
          <span className="text-sm font-semibold text-white">{algo.title}</span>
        </div>
        <p className="text-xs text-slate-400 italic leading-snug">
          &ldquo;{algo.query}&rdquo;
        </p>
      </div>

      {/* Flow */}
      <div className="px-4 py-4 flex-1 flex flex-col">
        {algo.steps.map((step, i) => {
          const isLast = i === algo.steps.length - 1;

          if (step.type === "node") {
            return (
              <div key={i} className="flex flex-col items-center">
                <div className={`w-full rounded-xl px-3 py-2 text-center ${
                  step.highlight
                    ? "bg-teal-600/25 border border-teal-500/40 text-teal-200"
                    : "bg-slate-700/40 border border-slate-600/30 text-slate-200"
                }`}>
                  <p className={`text-xs leading-snug ${step.highlight ? "font-semibold" : ""}`}>{step.text}</p>
                  {step.sub && <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{step.sub}</p>}
                </div>
                {!isLast && <Arrow />}
              </div>
            );
          }

          if (step.type === "branch") {
            return (
              <div key={i} className="flex flex-col items-center">
                <div className="flex gap-1.5 w-full">
                  {step.items.map((item) => (
                    <div key={item} className="flex-1 rounded-lg px-2 py-1.5 text-center bg-slate-900/60 border border-slate-600/20 text-slate-400 text-[10px]">
                      {item}
                    </div>
                  ))}
                </div>
                {!isLast && <Arrow />}
              </div>
            );
          }

          if (step.type === "note") {
            return (
              <div key={i} className="flex flex-col items-center">
                <div className="flex items-center gap-2 w-full py-0.5">
                  <div className="flex-1 h-px bg-slate-600/40" />
                  <span className="text-[10px] text-teal-500 italic flex-shrink-0">{step.text}</span>
                  <div className="flex-1 h-px bg-slate-600/40" />
                </div>
                {!isLast && <Arrow />}
              </div>
            );
          }

          return null;
        })}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-slate-700/40 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#5eead4" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          <p className="text-[10px] text-slate-400 leading-snug">{algo.source}</p>
        </div>
        <span className="text-[10px] text-slate-500 flex-shrink-0 ml-2">⚡ {algo.time}</span>
      </div>
    </div>
  );
}

function FlowchartSection() {
  return (
    <section className="py-24 bg-slate-900">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-teal-400 tracking-widest uppercase mb-3">
            Systematic output
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
            Clinical decision algorithms
          </h2>
          <p className="text-slate-400 max-w-lg mx-auto text-sm">
            Ask a diagnostic question — get a structured step-by-step algorithm grounded in specialist textbooks, in seconds.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {ALGORITHMS.map((algo) => (
            <AlgoCard key={algo.title} algo={algo} />
          ))}
        </div>

        <p className="text-center text-xs text-slate-500 mt-8">
          All algorithms are derived from cited peer-reviewed veterinary literature. Expert review is recommended before applying in clinical settings.
        </p>
      </div>
    </section>
  );
}

// ─── How it works (visual pipeline) ───────────────────────────────────────────
function HowItWorks() {
  const sources = [
    { label: "ScienceDirect (Elsevier)", icon: "🔬" },
    { label: "Scopus", icon: "📊" },
    { label: "Springer Nature", icon: "📙" },
    { label: "Taylor & Francis", icon: "📘" },
    { label: "108 Vet Journals (T&F)", icon: "🐾" },
  ];

  return (
    <section id="how-it-works" className="py-24 bg-slate-900 overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-20">
          <p className="text-sm font-semibold text-teal-400 tracking-widest uppercase mb-3">
            How it works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
            From question to cited answer<br className="hidden sm:block" /> in under 10 seconds
          </h2>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            Arlo retrieves, ranks, and synthesises evidence from trusted veterinary sources — then explains it clearly.
          </p>
        </div>

        {/* Pipeline diagram */}
        <div className="relative">
          {/* Horizontal connector (desktop) */}
          <div className="hidden lg:block absolute top-14 left-[12%] right-[12%] h-0.5 bg-gradient-to-r from-slate-700 via-teal-500 to-slate-700 z-0" />

          <div className="grid lg:grid-cols-4 gap-6 relative z-10">
            {/* Node 1: You ask */}
            <div className="flex flex-col items-center text-center">
              <div className="w-28 h-28 rounded-2xl bg-slate-900 border-2 border-slate-700 flex flex-col items-center justify-center gap-1 shadow-xl mb-5">
                <span className="text-3xl">💬</span>
                <span className="text-white text-xs font-semibold mt-1">You ask</span>
              </div>
              <h3 className="font-semibold text-white mb-2">Clinical question</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Plain language — drug dose, emergency protocol, differential diagnosis, anything.
              </p>
              <div className="mt-3 bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-xs text-slate-300 italic w-full">
                &ldquo;Safe ketamine dose for a 4 kg cat?&rdquo;
              </div>
            </div>

            {/* Node 2: AI processes */}
            <div className="flex flex-col items-center text-center">
              <div className="w-28 h-28 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 flex flex-col items-center justify-center gap-1 shadow-xl shadow-teal-900/50 mb-5">
                <span className="text-3xl">🧠</span>
                <span className="text-white text-xs font-semibold mt-1">AI processes</span>
              </div>
              <h3 className="font-semibold text-white mb-2">Query understanding</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Identifies species, drug, clinical context, and retrieves the most relevant knowledge chunks.
              </p>
              <div className="mt-3 flex flex-col gap-1 w-full">
                {["Species: Feline", "Drug: Ketamine", "Context: Anaesthesia"].map((t) => (
                  <div key={t} className="bg-teal-900/40 border border-teal-700/50 rounded-lg px-2.5 py-1 text-xs text-teal-300 text-left">{t}</div>
                ))}
              </div>
            </div>

            {/* Node 3: Knowledge base */}
            <div className="flex flex-col items-center text-center">
              <div className="w-28 h-28 rounded-2xl bg-slate-800 border-2 border-slate-600 flex flex-col items-center justify-center gap-1 shadow-lg mb-5">
                <span className="text-3xl">📚</span>
                <span className="text-slate-200 text-xs font-semibold mt-1">Knowledge</span>
              </div>
              <h3 className="font-semibold text-white mb-2">Trusted sources</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                Searches across a curated veterinary knowledge base.
              </p>
              <div className="flex flex-col gap-1 w-full">
                {sources.map((s) => (
                  <div key={s.label} className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1">
                    <span className="text-xs">{s.icon}</span>
                    <span className="text-xs text-slate-300">{s.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Node 4: Cited answer */}
            <div className="flex flex-col items-center text-center">
              <div className="w-28 h-28 rounded-2xl bg-teal-600 flex flex-col items-center justify-center gap-1 shadow-xl shadow-teal-900/50 mb-5">
                <span className="text-3xl">✅</span>
                <span className="text-white text-xs font-semibold mt-1">You receive</span>
              </div>
              <h3 className="font-semibold text-white mb-2">Cited answer</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                Clear, structured response with the exact sources cited — verifiable and shareable.
              </p>
              <div className="bg-teal-900/30 border border-teal-700/50 rounded-xl px-3 py-2 text-xs text-teal-200 text-left w-full">
                <p className="font-semibold mb-1">2–4 mg/kg IV ketamine</p>
                <p className="text-teal-400">📖 Veterinary Anaesthesia &amp; Analgesia — Springer Nature</p>
              </div>
            </div>
          </div>

          {/* Mobile vertical connector */}
          <div className="lg:hidden absolute top-28 left-1/2 -translate-x-1/2 w-0.5 bg-gradient-to-b from-slate-700 via-teal-500 to-slate-700" style={{ height: "calc(100% - 7rem)" }} />
        </div>

        {/* Bottom note */}
        <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 text-sm text-slate-500 px-4 sm:px-0">
          {[
            { icon: "⚡", label: "< 10 second response time" },
            { icon: "📖", label: "Every answer is cited" },
            { icon: "🔒", label: "GDPR compliant" },
            { icon: "🌐", label: "Works on any device" },
          ].map((i) => (
            <div key={i.label} className="flex items-center justify-center gap-2 text-center">
              <span className="text-base sm:text-sm">{i.icon}</span>
              <span className="text-xs sm:text-sm leading-tight">{i.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── For Clinics ──────────────────────────────────────────────────────────────
function ForClinics() {
  return (
    <section id="for-clinics" className="py-24 bg-slate-900">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-5">
          {[
            { stat: "10×", label: "faster than manual lookup" },
            { stat: "500+", label: "veterinary professionals" },
            { stat: "98%", label: "answer accuracy rate" },
            { stat: "24/7", label: "available, no downtime" },
          ].map((item) => (
            <div
              key={item.label}
              className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/8 transition-colors"
            >
              <p className="text-4xl font-bold text-teal-400 mb-1">{item.stat}</p>
              <p className="text-sm text-slate-400">{item.label}</p>
            </div>
          ))}
        </div>

        {/* Copy */}
        <div>
          <p className="text-sm font-semibold text-teal-400 tracking-widest uppercase mb-4">
            For clinics &amp; practices
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-6">
            Equip your entire team with instant clinical intelligence
          </h2>
          <p className="text-slate-400 leading-relaxed mb-8">
            Deploy Arlo across your clinic. Every vet, nurse, and student gets
            instant access to evidence-based answers — reducing errors, accelerating
            consultations, and improving patient outcomes.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-6 py-3.5 bg-teal-600 hover:bg-teal-500 text-white font-semibold rounded-xl transition-all shadow-lg hover:shadow-teal-500/20"
          >
            Get started for your clinic →
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── CTA ──────────────────────────────────────────────────────────────────────
function CTASection() {
  return (
    <section className="py-24 bg-gradient-to-br from-teal-600 to-teal-800 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            "radial-gradient(circle at 2px 2px, white 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />
      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
          Ready to transform how you practise?
        </h2>
        <p className="text-teal-100 mb-10 text-lg">
          Join 500+ vets already using Arlo. Free during beta.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/register"
            className="px-8 py-4 bg-white text-teal-700 font-bold rounded-xl hover:bg-teal-50 transition-all shadow-xl hover:-translate-y-0.5"
          >
            Start for free
          </Link>
          <Link
            href="/login"
            className="px-8 py-4 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all"
          >
            Log in to your account
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 py-8">
      <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center">
            <span className="text-white text-xs">🐾</span>
          </div>
          <span className="text-slate-500">
            &copy; {new Date().getFullYear()} Arlo. All rights reserved.
          </span>
        </div>
        <div className="flex gap-6">
          {["Features", "How it works", "Privacy Policy", "Terms of Service"].map((l) => (
            <a key={l} href="#" className="hover:text-teal-400 transition-colors">{l}</a>
          ))}
        </div>
      </div>
    </footer>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="font-[family-name:var(--font-geist-sans)]">
      <Navbar />
      <Hero />
      <FeaturesSection />
      <ExamplesSection />
      <FlowchartSection />
      <HowItWorks />
      <ForClinics />
      <CTASection />
      <Footer />
    </div>
  );
}
