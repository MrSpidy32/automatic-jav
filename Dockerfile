FROM unclecode/crawl4ai:0.9.3
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN chmod +x run_pipeline.sh missav_pipeline.sh onejav_pipeline.sh javct_pipeline.sh aggregator_pipeline.sh scripts/*.sh scripts/*.py || true
CMD ["bash", "./run_pipeline.sh"]