import React, { useState, useRef, useEffect } from "react";
import "./FaqChatbot.css";

const API = "/api";

// SCRUM-28: AI chatbot that answers members' FAQs.
export default function FaqChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      from: "bot",
      text: "Hi! I'm the FAQ assistant. Ask me a question and I'll do my best to help.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open]);

  const send = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { from: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/chatbot/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          from: "bot",
          text: data.answer || "Sorry, I couldn't find an answer.",
          suggestions: data.suggestions || null,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { from: "bot", text: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const askSuggestion = (text) => {
    setInput(text);
    // Submit on the next tick so the input reflects the chosen question.
    setTimeout(() => {
      setInput("");
      setMessages((prev) => [...prev, { from: "user", text }]);
      setLoading(true);
      fetch(`${API}/chatbot/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question: text }),
      })
        .then((r) => r.json())
        .then((data) =>
          setMessages((prev) => [
            ...prev,
            {
              from: "bot",
              text: data.answer || "Sorry, I couldn't find an answer.",
              suggestions: data.suggestions || null,
            },
          ])
        )
        .catch(() =>
          setMessages((prev) => [
            ...prev,
            { from: "bot", text: "Something went wrong. Please try again." },
          ])
        )
        .finally(() => setLoading(false));
    }, 0);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {!open && (
        <button
          className="faqbot-fab"
          onClick={() => setOpen(true)}
          aria-label="Open FAQ assistant"
          title="FAQ assistant"
        >
          💬
        </button>
      )}

      {open && (
        <div className="faqbot-panel" role="dialog" aria-label="FAQ assistant">
          <div className="faqbot-header">
            <span className="faqbot-header__title">🤖 FAQ Assistant</span>
            <button
              className="faqbot-close"
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div className="faqbot-messages" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`faqbot-msg faqbot-msg--${m.from}`}>
                <div className="faqbot-bubble">{m.text}</div>
                {m.suggestions && (
                  <div className="faqbot-suggestions">
                    {m.suggestions.map((s, j) => (
                      <button
                        key={j}
                        className="faqbot-suggestion"
                        onClick={() => askSuggestion(s)}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="faqbot-msg faqbot-msg--bot">
                <div className="faqbot-bubble faqbot-bubble--typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
          </div>

          <div className="faqbot-input-row">
            <input
              className="faqbot-input"
              placeholder="Type your question…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button
              className="faqbot-send"
              onClick={send}
              disabled={loading || !input.trim()}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
