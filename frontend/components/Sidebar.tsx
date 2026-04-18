"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ConversationSummary, User } from "@/types/chat";

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

interface SidebarProps {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  onLogout: () => void;
  isLoadingConversations?: boolean;
}

export default function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  isOpen,
  onClose,
  user,
  onLogout,
  isLoadingConversations,
}: SidebarProps) {
  const pathname = usePathname();
  const base =
    "flex flex-col h-full w-64 bg-white border-r border-gray-200 z-40 transition-transform duration-200";
  const mobile = isOpen
    ? "fixed inset-y-0 left-0 translate-x-0 shadow-xl"
    : "fixed inset-y-0 left-0 -translate-x-full";

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 md:hidden animate-fade-in"
          onClick={onClose}
        />
      )}

      <aside className={`${base} ${mobile} md:static md:translate-x-0 md:shadow-none`}>
        {/* New chat */}
        <div className="p-3 border-b border-gray-100">
          <button
            onClick={onNewChat}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            + New Chat
          </button>
        </div>

        {/* Nav links for logged-in users */}
        {user && (
          <div className="px-3 py-2 border-b border-gray-100 flex flex-col gap-1">
            <Link
              href="/"
              onClick={onClose}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                pathname === "/" ? "bg-teal-50 text-teal-700" : "text-slate-500 hover:bg-gray-100 hover:text-slate-800"
              }`}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              Home
            </Link>
            <Link
              href="/profile"
              onClick={onClose}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                pathname === "/profile" ? "bg-teal-50 text-teal-700" : "text-slate-500 hover:bg-gray-100 hover:text-slate-800"
              }`}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
              My Account
            </Link>
          </div>
        )}

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto py-2">
          {!user ? (
            <p className="text-xs text-slate-400 text-center px-4 py-6">
              Sign in to save conversations
            </p>
          ) : isLoadingConversations ? (
            // Shimmer skeleton
            <div className="space-y-1 px-2 pt-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-10 rounded-lg bg-gradient-to-r from-slate-100 via-slate-200 to-slate-100 bg-[length:200%_100%] animate-shimmer"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-xs text-slate-400 text-center px-4 py-6">
              No conversations yet
            </p>
          ) : (
            <>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide px-3 mb-1">
                Recent
              </p>
              <ul>
                {conversations.map((conv, i) => (
                  <li
                    key={conv.id}
                    className="group relative animate-slide-up"
                    style={{ animationDelay: `${i * 30}ms` }}
                  >
                    <button
                      onClick={() => onSelectConversation(conv.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg mx-1 transition-colors ${
                        activeConversationId === conv.id
                          ? "bg-teal-100 text-teal-800 font-medium"
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      <p className="text-xs font-medium truncate pr-6">
                        {conv.title}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {relativeTime(conv.updated_at)}
                      </p>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="absolute right-2 top-2 invisible group-hover:visible text-gray-400 hover:text-red-500 text-xs px-1 py-0.5 rounded transition-colors"
                      title="Delete"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        {/* User info + profile + logout */}
        <div className="border-t border-gray-100 p-3">
          {user ? (
            <>
              <div className="flex items-center justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-700 truncate">
                    {user.full_name}
                  </p>
                  {user.clinic && (
                    <p className="text-xs text-gray-400 truncate">{user.clinic}</p>
                  )}
                </div>
                <Link
                  href="/profile"
                  className="shrink-0 ml-2 text-gray-400 hover:text-teal-600 transition-colors"
                  title="Edit profile"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </Link>
              </div>
              <button
                onClick={onLogout}
                className="mt-2 w-full text-left text-xs text-slate-500 hover:text-red-500 transition-colors flex items-center gap-1.5"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Sign out
              </button>
            </>
          ) : (
            <div className="flex gap-2">
              <Link
                href="/login"
                className="flex-1 text-center text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg py-1.5 transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="flex-1 text-center text-xs text-white bg-teal-600 hover:bg-teal-700 rounded-lg py-1.5 transition-colors"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
