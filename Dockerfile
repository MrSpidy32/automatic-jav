FROM ghcr.io/guiltjay/crawl4ai:latest
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN chmod +x run_pipeline.sh missav_pipeline.sh onejav_pipeline.sh javct_pipeline.sh aggregator_pipeline.sh scripts/*.sh scripts/*.py || true
CMD ["bash", "./run_pipeline.sh"] 