"use client";

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
}: SidebarProps) {
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
          className="fixed inset-0 bg-black/30 z-30 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Desktop: static, Mobile: overlay */}
      <aside className={`${base} ${mobile} md:static md:translate-x-0 md:shadow-none`}>
        {/* New chat */}
        <div className="p-3 border-b border-gray-100">
          <button
            onClick={onNewChat}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            + New Chat
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto py-2">
          {conversations.length === 0 ? (
            <p className="text-xs text-gray-400 text-center px-4 py-6">
              No conversations yet
            </p>
          ) : (
            <>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-3 mb-1">
                Recent
              </p>
              <ul>
                {conversations.map((conv) => (
                  <li key={conv.id} className="group relative">
                    <button
                      onClick={() => onSelectConversation(conv.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg mx-1 transition-colors ${
                        activeConversationId === conv.id
                          ? "bg-blue-50 text-blue-700"
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
                    {/* Delete button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="absolute right-2 top-2 invisible group-hover:visible text-gray-400 hover:text-red-500 text-xs px-1 py-0.5 rounded"
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

        {/* User info + logout */}
        {user && (
          <div className="border-t border-gray-100 p-3">
            <p className="text-xs font-medium text-gray-700 truncate">
              {user.full_name}
            </p>
            {user.clinic && (
              <p className="text-xs text-gray-400 truncate">{user.clinic}</p>
            )}
            <button
              onClick={onLogout}
              className="mt-2 text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              Sign out
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
