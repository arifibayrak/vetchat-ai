"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

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
          ? "bg-white/95 backdrop-blur-sm border-b border-slate-100 shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center shadow-sm group-hover:shadow-teal-200 transition-shadow">
            <span className="text-white text-sm">🐾</span>
          </div>
          <span className={`font-semibold text-[15px] tracking-tight transition-colors ${scrolled ? "text-slate-900" : "text-white"}`}>
            VetChat <span className="text-teal-400">AI</span>
          </span>
        </a>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {["Features", "How it works", "For Clinics", "Pricing"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}
              className={`px-3.5 py-2 text-sm rounded-md transition-colors ${
                scrolled
                  ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  : "text-white/80 hover:text-white hover:bg-white/10"
              }`}
            >
              {item}
            </a>
          ))}
        </nav>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className={`text-sm px-4 py-2 rounded-md transition-colors ${
              scrolled ? "text-slate-600 hover:text-slate-900" : "text-white/80 hover:text-white"
            }`}
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="text-sm px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium transition-all shadow-sm hover:shadow-teal-200/50 hover:shadow-md"
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
          <div className={`space-y-1.5 transition-all ${menuOpen ? "rotate-45" : ""}`}>
            <span className={`block w-5 h-0.5 transition-colors ${scrolled ? "bg-slate-700" : "bg-white"}`} />
            <span className={`block w-5 h-0.5 transition-colors ${scrolled ? "bg-slate-700" : "bg-white"} ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block w-5 h-0.5 transition-colors ${scrolled ? "bg-slate-700" : "bg-white"}`} />
          </div>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-white border-b border-slate-100 px-6 py-4 space-y-2">
          {["Features", "How it works", "For Clinics", "Pricing"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}
              className="block py-2 text-sm text-slate-700 hover:text-teal-600"
              onClick={() => setMenuOpen(false)}
            >
              {item}
            </a>
          ))}
          <div className="pt-2 flex flex-col gap-2">
            <Link href="/login" className="text-sm text-center py-2.5 border border-slate-200 rounded-lg text-slate-700">
              Log in
            </Link>
            <Link href="/register" className="text-sm text-center py-2.5 bg-teal-600 rounded-lg text-white font-medium">
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
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
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

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent" />
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
          <span className="text-slate-400 text-xs font-medium">VetChat AI</span>
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
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-teal-600 tracking-widest uppercase mb-3">
            What VetChat AI does
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight mb-4">
            Everything a vet needs,<br className="hidden sm:block" /> right at the point of care
          </h2>
          <p className="text-slate-500 max-w-xl mx-auto">
            Built specifically for veterinary professionals — not a general-purpose chatbot repurposed for medicine.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group p-8 rounded-2xl border border-slate-200 bg-white hover:border-teal-200 hover:shadow-xl hover:shadow-teal-50 transition-all duration-300 hover:-translate-y-1"
            >
              <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center text-2xl mb-5 group-hover:bg-teal-100 transition-colors">
                {f.icon}
              </div>
              <div className="inline-block px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-700 text-xs font-medium mb-3">
                {f.tag}
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-3">{f.title}</h3>
              <p className="text-slate-500 leading-relaxed text-sm">{f.description}</p>
              <div className="mt-5 text-teal-600 text-sm font-medium group-hover:text-teal-700 flex items-center gap-1.5">
                Learn more <span className="group-hover:translate-x-0.5 transition-transform inline-block">→</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How it works ──────────────────────────────────────────────────────────────
const STEPS = [
  {
    number: "01",
    title: "Ask your question",
    description:
      "Type your clinical question in plain language — drug dosage, differential diagnosis, treatment protocol, or anything else.",
  },
  {
    number: "02",
    title: "AI retrieves evidence",
    description:
      "VetChat AI searches its curated veterinary knowledge base — textbooks, journals, pharmacology references — to find the most relevant clinical information.",
  },
  {
    number: "03",
    title: "Get a cited answer",
    description:
      "Receive a clear, concise answer with cited sources so you can verify the information and share it with confidence.",
  },
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 bg-slate-50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-teal-600 tracking-widest uppercase mb-3">
            How it works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight mb-4">
            From question to answer<br className="hidden sm:block" /> in under 10 seconds
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-10 left-1/3 right-1/3 h-px bg-gradient-to-r from-teal-200 to-teal-200" />

          {STEPS.map((step, i) => (
            <div key={step.number} className="relative">
              <div className="flex items-center gap-4 mb-5">
                <div className="w-10 h-10 rounded-full bg-teal-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0 shadow-lg shadow-teal-100">
                  {i + 1}
                </div>
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block flex-1 h-px bg-slate-200" />
                )}
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-3">{step.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{step.description}</p>
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
            Deploy VetChat AI across your clinic. Every vet, nurse, and student gets
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
          Join 500+ vets already using VetChat AI. Free during beta.
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
            &copy; {new Date().getFullYear()} VetChat AI. All rights reserved.
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
      <HowItWorks />
      <ForClinics />
      <CTASection />
      <Footer />
    </div>
  );
}
