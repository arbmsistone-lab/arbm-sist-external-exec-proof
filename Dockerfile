FROM node:24-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates bash \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/arbm
COPY scripts /opt/arbm/scripts
RUN mkdir -p /tmp/arbm-continuity/run \
 && chown -R node:node /opt/arbm /tmp/arbm-continuity

ENV NODE_ENV=production \
    PORT=8000 \
    ARBM_RUN_ROOT=/tmp/arbm-continuity/run
USER node
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD node -e "fetch('http://127.0.0.1:8000/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["node","/opt/arbm/scripts/persistent-container-health.mjs"]
