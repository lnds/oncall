package main

import (
	"fmt"
	"sync"
	"testing"
)

func TestStoreAssignsIncreasingIDs(t *testing.T) {
	s := NewStore()
	a := s.Add(Notification{Person: "Ana"})
	b := s.Add(Notification{Person: "Beto"})
	if b.ID <= a.ID {
		t.Fatalf("expected increasing ids, got %d then %d", a.ID, b.ID)
	}
}

func TestStoreRecentNewestFirst(t *testing.T) {
	s := NewStore()
	s.Add(Notification{Person: "Ana"})
	s.Add(Notification{Person: "Beto"})
	recent := s.Recent()
	if len(recent) != 2 {
		t.Fatalf("expected 2 notifications, got %d", len(recent))
	}
	if recent[0].Person != "Beto" {
		t.Errorf("expected newest first, got %q", recent[0].Person)
	}
}

func TestStoreKeepsAtMostCapacity(t *testing.T) {
	s := NewStore()
	for i := 0; i < Capacity+20; i++ {
		s.Add(Notification{Person: fmt.Sprintf("p%d", i)})
	}
	if got := len(s.Recent()); got != Capacity {
		t.Fatalf("expected %d notifications, got %d", Capacity, got)
	}
}

func TestStoreConcurrentAdds(t *testing.T) {
	s := NewStore()
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.Add(Notification{Person: "x"})
		}()
	}
	wg.Wait()
	if got := len(s.Recent()); got != 50 {
		t.Fatalf("expected 50 notifications, got %d", got)
	}
}
