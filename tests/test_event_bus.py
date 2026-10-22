class TestEventBus:

    def test_publish_subscribe_receives_data(self, event_bus):
        received = []
        event_bus.subscribe("test.topic", lambda d: received.append(d))
        event_bus.publish("test.topic", {"msg": "hello"})
        assert len(received) == 1
        assert received[0]["msg"] == "hello"

    def test_multiple_subscribers_all_receive(self, event_bus):
        r1, r2 = [], []
        event_bus.subscribe("test.topic", lambda d: r1.append(d))
        event_bus.subscribe("test.topic", lambda d: r2.append(d))
        event_bus.publish("test.topic", {"n": 1})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_unsubscribe_stops_receiving(self, event_bus):
        received = []
        sub = event_bus.subscribe("test.topic", lambda d: received.append(d))
        event_bus.publish("test.topic", {"n": 1})
        assert len(received) == 1
        event_bus.unsubscribe(sub)
        event_bus.publish("test.topic", {"n": 2})
        assert len(received) == 1

    def test_different_topics_isolated(self, event_bus):
        r1, r2 = [], []
        event_bus.subscribe("topic.a", lambda d: r1.append(d))
        event_bus.subscribe("topic.b", lambda d: r2.append(d))
        event_bus.publish("topic.a", {"n": 1})
        assert len(r1) == 1
        assert len(r2) == 0

    def test_handler_error_does_not_crash_bus(self, event_bus):
        received = []
        event_bus.subscribe("test.topic", lambda d: (_ for _ in ()).throw(Exception("boom")))
        event_bus.subscribe("test.topic", lambda d: received.append(d))
        event_bus.publish("test.topic", {"n": 1})
        assert len(received) == 1

    def test_clear_removes_all_subscribers(self, event_bus):
        received = []
        event_bus.subscribe("test.topic", lambda d: received.append(d))
        event_bus.clear()
        event_bus.publish("test.topic", {"n": 1})
        assert len(received) == 0
