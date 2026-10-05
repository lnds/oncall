package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer() http.Handler {
	return NewServer(NewStore(), slog.New(slog.NewJSONHandler(io.Discard, nil)))
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	rec := do(t, newTestServer(), "GET", "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestNotifyAccepted(t *testing.T) {
	rec := do(t, newTestServer(), "POST", "/notify",
		`{"person":"Ana Soto","email":"ana@example.com","message":"[SEV2] Latencia alta","incident_id":7,"severity":2}`)
	if rec.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d: %s", rec.Code, rec.Body.String())
	}
}

func TestNotifyRequiresFields(t *testing.T) {
	h := newTestServer()
	cases := map[string]string{
		"sin person":  `{"email":"ana@example.com","message":"hola"}`,
		"sin email":   `{"person":"Ana","message":"hola"}`,
		"sin message": `{"person":"Ana","email":"ana@example.com"}`,
		"en blanco":   `{"person":"  ","email":"ana@example.com","message":"hola"}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			rec := do(t, h, "POST", "/notify", body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d", rec.Code)
			}
		})
	}
}

func TestNotifyRejectsInvalidJSON(t *testing.T) {
	rec := do(t, newTestServer(), "POST", "/notify", `{not json`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}

func TestListNotifications(t *testing.T) {
	h := newTestServer()
	do(t, h, "POST", "/notify", `{"person":"Ana","email":"ana@example.com","message":"uno"}`)
	do(t, h, "POST", "/notify", `{"person":"Beto","email":"beto@example.com","message":"dos"}`)

	rec := do(t, h, "GET", "/notifications", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var got []map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 notifications, got %d", len(got))
	}
	if got[0]["message"] != "dos" {
		t.Errorf("expected newest first, got %v", got[0]["message"])
	}
	if _, ok := got[0]["sent_at"]; !ok {
		t.Errorf("expected sent_at in notification")
	}
}

func TestMethodNotAllowed(t *testing.T) {
	rec := do(t, newTestServer(), "GET", "/notify", "")
	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", rec.Code)
	}
}
