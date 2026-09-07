FROM ghcr.io/guiltjay/crawl4ai:575087806e3a8a98512a44548ecef7865f4c6eb7@sha256:8935f76c0bb28f68d38e0d5c3ec37dfc7e5af0a505300ebfde639c726d07d4a9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN chmod +x run_pipeline.sh missav_pipeline.sh onejav_pipeline.sh javct_pipeline.sh aggregator_pipeline.sh scripts/*.sh scripts/*.py || true
CMD ["bash", "./run_pipeline.sh"]