package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

type notifyRequest struct {
	Person     string `json:"person"`
	Email      string `json:"email"`
	Message    string `json:"message"`
	IncidentID *int64 `json:"incident_id"`
	Severity   *int   `json:"severity"`
}

type notificationJSON struct {
	Notification
	SentAt string `json:"sent_at"`
}

func NewServer(store *Store, logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	mux.HandleFunc("POST /notify", func(w http.ResponseWriter, r *http.Request) {
		var req notifyRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON body")
			return
		}
		if strings.TrimSpace(req.Person) == "" || strings.TrimSpace(req.Email) == "" || strings.TrimSpace(req.Message) == "" {
			writeError(w, http.StatusBadRequest, "person, email and message are required")
			return
		}
		n := store.Add(Notification{
			Person:     req.Person,
			Email:      req.Email,
			Message:    req.Message,
			IncidentID: req.IncidentID,
			Severity:   req.Severity,
		})
		logger.Info("notification_sent",
			"id", n.ID, "person", n.Person, "email", n.Email,
			"message", n.Message, "incident_id", n.IncidentID, "severity", n.Severity)
		writeJSON(w, http.StatusAccepted, map[string]any{"id": n.ID, "status": "sent"})
	})

	mux.HandleFunc("GET /notifications", func(w http.ResponseWriter, r *http.Request) {
		recent := store.Recent()
		out := make([]notificationJSON, len(recent))
		for i, n := range recent {
			out[i] = notificationJSON{Notification: n, SentAt: n.SentAt.UTC().Format(time.RFC3339)}
		}
		writeJSON(w, http.StatusOK, out)
	})

	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
