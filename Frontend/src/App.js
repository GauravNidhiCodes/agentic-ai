import { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import "./App.css";
 
/* ── Code Block ── */
function CodeBlock({ language, children }) {
  const [copied, setCopied] = useState(false);
  const code = String(children).replace(/\n$/, "");
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span>{language || "code"}</span>
        <button className={`copy-btn ${copied ? "copied" : ""}`} onClick={handleCopy}>
          {copied ? "✓ Copied!" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter style={oneDark} language={language || "text"} PreTag="pre"
        customStyle={{ margin: 0, padding: "16px", background: "#111", fontSize: "13px" }}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
 
const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    if (!inline && match) return <CodeBlock language={match[1]}>{children}</CodeBlock>;
    if (!inline && String(children).includes("\n")) return <CodeBlock>{children}</CodeBlock>;
    return <code className={className} {...props}>{children}</code>;
  },
};
 
/* ── Tool Icons ── */
const TOOL_ICONS = {
  web_search: "🌐",
  calculator: "🧮",
  file_reader: "📄",
  python_executor: "🐍",
  memory_search: "🧠",
  datetime: "🕐",
};
 
/* ── Agent Steps Panel ── */
function AgentSteps({ steps }) {
  const [open, setOpen] = useState(false);
  if (!steps || steps.length === 0) return null;
 
  const actionSteps = steps.filter((s) => s.type === "action");
  const toolsUsed = [...new Set(actionSteps.map((s) => s.tool).filter(Boolean))];
 
  return (
    <div className="agent-steps-container">
      <button className="steps-toggle" onClick={() => setOpen(!open)}>
        <span className="steps-icon">⚡</span>
        <span>
          {actionSteps.length} step{actionSteps.length !== 1 ? "s" : ""}
          {toolsUsed.length > 0 && (
            <span className="tools-used">
              {toolsUsed.map((t) => (
                <span key={t} className="tool-chip">
                  {TOOL_ICONS[t] || "🔧"} {t}
                </span>
              ))}
            </span>
          )}
        </span>
        <span className="chevron">{open ? "▲" : "▼"}</span>
      </button>
 
      {open && (
        <div className="steps-panel">
          {steps.map((step, i) => (
            <div key={i} className={`step-item step-${step.type}`}>
              <div className="step-header">
                <span className="step-num">Step {step.iteration}</span>
                <span className={`step-badge badge-${step.type}`}>
                  {step.type === "action"
                    ? `${TOOL_ICONS[step.tool] || "🔧"} ${step.tool}`
                    : "✅ Final"}
                </span>
              </div>
 
              {step.thought && (
                <div className="step-section">
                  <div className="step-label">💭 Thought</div>
                  <div className="step-content thought-text">{step.thought}</div>
                </div>
              )}
 
              {step.tool_input && Object.keys(step.tool_input).length > 0 && (
                <div className="step-section">
                  <div className="step-label">📥 Input</div>
                  <pre className="step-content code-text">
                    {JSON.stringify(step.tool_input, null, 2)}
                  </pre>
                </div>
              )}
 
              {step.observation && (
                <div className="step-section">
                  <div className="step-label">👁 Observation</div>
                  <div className="step-content obs-text">{step.observation}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
 
/* ── Message ── */
function Message({ role, text, steps }) {
  return (
    <div className={`message-row ${role}`}>
      <div className="message-content">
        <div className={`avatar ${role === "user" ? "user-avatar" : "ai-avatar"}`}>
          {role === "user" ? "U" : "⚡"}
        </div>
        <div className="message-body">
          <div className="message-text">
            {role === "ai" ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {text}
              </ReactMarkdown>
            ) : (
              <p>{text}</p>
            )}
          </div>
          {role === "ai" && steps && <AgentSteps steps={steps} />}
        </div>
      </div>
    </div>
  );
}
 
/* ── Typing Indicator ── */
function TypingIndicator() {
  return (
    <div className="message-row ai">
      <div className="message-content">
        <div className="avatar ai-avatar">⚡</div>
        <div className="message-body">
          <div className="typing-indicator">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        </div>
      </div>
    </div>
  );
}
 
/* ── Main App ── */
export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [chatId, setChatId] = useState("default");
  const [chatList, setChatList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
 
  const API = "http://127.0.0.1:8000";
 
  const parseSteps = (raw) => {
    if (!raw) return [];
    try {
      return JSON.parse(raw.replace(/'/g, '"'));
    } catch {
      return [];
    }
  };
 
  useEffect(() => {
    fetch(`${API}/history?chat_id=${chatId}`)
      .then((r) => r.json())
      .then((data) => {
        const formatted = data.flatMap((c) => [
          { role: "user", text: c.user },
          { role: "ai", text: c.ai, steps: parseSteps(c.steps) },
        ]);
        setMessages(formatted);
      })
      .catch(() => {});
  }, [chatId]);
 
  const fetchChatList = useCallback(() => {
    fetch(`${API}/chats`)
      .then((r) => r.json())
      .then(setChatList)
      .catch(() => {});
  }, []);
 
  useEffect(() => {
    fetchChatList();
  }, [fetchChatList]);
 
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);
 
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 180) + "px";
    }
  }, [input]);
 
  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userText = input.trim();
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setInput("");
    setLoading(true);
 
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: userText, chat_id: chatId }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: data.answer || data.error || "Something went wrong.",
          steps: data.steps || [],
        },
      ]);
      fetchChatList();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "ai", text: "⚠️ Could not reach the backend.", steps: [] },
      ]);
    } finally {
      setLoading(false);
    }
  };
 
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };
 
  const startNewChat = () => {
    setChatId(Date.now().toString());
    setMessages([]);
    setSidebarOpen(false);
  };
 
  return (
    <div className="app-container">
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}
 
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-icon">⚡</span>
            <span className="brand-name">AgentOS</span>
          </div>
          <button className="new-chat-btn" onClick={startNewChat}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New chat
          </button>
        </div>
 
        <div className="chat-list">
          {chatList.length === 0 && (
            <div className="empty-chats">No chats yet</div>
          )}
          {chatList.map((chat) => (
            <div
              key={chat.chat_id}
              className={`chat-item ${chat.chat_id === chatId ? "active" : ""}`}
              onClick={() => {
                setChatId(chat.chat_id);
                setSidebarOpen(false);
              }}
            >
              <span className="chat-item-icon">💬</span>
              <span className="chat-item-title">{chat.title || "Untitled"}</span>
            </div>
          ))}
        </div>
 
        <div className="sidebar-footer">
          <div className="model-info">
            <span className="model-dot" />
            Llama 3.3 70B via Groq
          </div>
        </div>
      </div>
 
      {/* Main */}
      <div className="main-area">
        <div className="chat-header">
          <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <div className="header-center">
            <h2>AgentOS</h2>
            <span className="model-badge">Agentic · ReAct · 6 Tools</span>
          </div>
          <div style={{ width: 36 }} />
        </div>
 
        <div className="messages-container">
          {messages.length === 0 && !loading && (
            <div className="empty-state">
              <div className="empty-state-icon">⚡</div>
              <h3>AgentOS is ready</h3>
              <p>I can search the web, run code, calculate, and remember.</p>
              <div className="capability-chips">
                {Object.entries(TOOL_ICONS).map(([tool, icon]) => (
                  <span key={tool} className="cap-chip">
                    {icon} {tool.replace("_", " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
 
          {messages.map((msg, i) => (
            <Message key={i} role={msg.role} text={msg.text} steps={msg.steps} />
          ))}
 
          {loading && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>
 
        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              className="input-box"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything — I'll think, search, and act..."
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
          <div className="input-footer">
            AgentOS · ReAct loop · Web search · Code execution · Memory
          </div>
        </div>
      </div>
    </div>
  );
}
 