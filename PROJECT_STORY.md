## Inspiration

Every year, retailers lose billions of dollars to **promotion cannibalization** — the hidden phenomenon where discounted products steal sales from full-price items instead of generating new revenue. Traditional analytics catch this problem days or weeks later, after the damage is done. We asked: *What if we could detect and respond to cannibalization in real-time, the moment it happens?*

The combination of Confluent's real-time data streaming and Google's Gemini AI gave us the perfect toolkit to tackle this challenge. We envisioned an intelligent system that doesn't just report problems — it explains them, recommends solutions, and learns from every action taken.

## What it does

**TrueLift AI** is a real-time promotion intelligence platform that:

1. **Streams sales data** through Confluent Kafka as virtual shoppers generate purchase events
2. **Detects cannibalization** using ML models that compare actual vs. predicted sales in 1-minute windows
3. **Generates AI strategies** via Gemini Pro, providing human-readable explanations and actionable recommendations
4. **Enables instant response** — managers can stop promotions, adjust prices, or target segments with one click
5. **Measures effectiveness** through a feedback loop that tracks the impact of every action

The system calculates revenue loss in real-time using:

$$\text{Loss} = (\text{Predicted Sales} - \text{Actual Sales}) \times \text{Promo Price}$$

When loss exceeds thresholds, alerts are generated with severity levels (low/medium/high) based on the loss percentage.

## How we built it

**Architecture:**
- **Frontend**: Next.js 14 with real-time WebSocket updates
- **Backend**: FastAPI serving REST endpoints and WebSocket connections
- **Streaming**: Confluent Cloud Kafka for event-driven architecture
- **AI**: Google Gemini Pro for strategy generation
- **Database**: PostgreSQL for persistence, Redis for caching
- **Deployment**: Google Cloud Run with auto-scaling

**Data Flow:**
```
Virtual Shoppers → Kafka [sales-events] → ML Detector 
    → Kafka [cannibalization-alerts] → Gemini Agent 
    → Backend API → WebSocket → Dashboard
```

**Key Services:**
- `virtual-shoppers`: Simulates realistic shopping behavior
- `ml-detector`: Aggregates events and detects anomalies
- `gemini-agent`: Consumes alerts and generates AI strategies
- `feedback-loop`: Monitors action effectiveness

## Challenges we ran into

1. **Real-time consistency**: Ensuring alerts, strategies, and feedback stay synchronized across distributed services required careful Kafka topic design and idempotent processing.

2. **Cold start latency**: Cloud Run's serverless model means services scale to zero. We optimized container sizes and implemented health checks to minimize first-request delays.

3. **Gemini rate limits**: During burst scenarios, we implemented queuing and fallback strategies to handle API throttling gracefully.

4. **Database schema evolution**: As we added features like burst tracking and feedback metrics, we had to carefully migrate schemas without losing data.

5. **WebSocket reliability**: Maintaining persistent connections for real-time updates required implementing automatic reconnection logic on the frontend.

## Accomplishments that we're proud of

- **End-to-end real-time pipeline**: From event generation to AI strategy display in under 3 seconds
- **Production-ready deployment**: All 6 services running on GCP Cloud Run with proper secret management
- **Feedback loop**: The system doesn't just detect problems — it measures whether solutions work
- **Clean architecture**: Event-driven microservices that can scale independently
- **Live demo mode**: One-click burst simulation that showcases the entire pipeline

## What we learned

- **Confluent Cloud** makes Kafka accessible and production-ready without the operational overhead
- **Gemini Pro** excels at generating contextual, actionable business recommendations
- **Event-driven architecture** is ideal for real-time AI applications where timing matters
- **The power of feedback loops**: Measuring action effectiveness creates a self-improving system
- **GCP's ecosystem**: Cloud Run + Cloud SQL + Secret Manager work seamlessly together

## What's next for TrueLift AI

1. **Confluent Flink integration**: Use Flink SQL for more sophisticated real-time aggregations and windowing
2. **Predictive models**: Train on historical feedback data to predict which strategies will work best
3. **Multi-store expansion**: Support for regional and store-level analysis
4. **Automated actions**: Allow the system to take pre-approved actions without human intervention
5. **RAG enhancement**: Integrate with product catalogs and competitor data for richer AI context
6. **Mobile alerts**: Push notifications for urgent cannibalization events
