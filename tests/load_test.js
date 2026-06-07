// k6 load test for Resume Tailor API
// Run:  k6 run tests/load_test.js 2>&1 | tee tests/k6_report.txt

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const rateLimited = new Rate('rate_limited');
const apiLatency = new Trend('api_latency');

export const options = {
  stages: [
    { duration: '5s', target: 3 },
    { duration: '15s', target: 8 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    errors: ['rate<0.05'],
  },
};

const BASE = 'http://127.0.0.1:5001';
const PAYLOAD = JSON.stringify({
  company_name: 'RateLoadTest',
  job_description: 'Looking for a senior software engineer with Python experience.',
});
const HEADERS = { 'Content-Type': 'application/json' };

export default function () {
  // 1. Health check
  let h = http.get(`${BASE}/health`);
  check(h, { 'health 200': (r) => r.status === 200 });

  // 2. Generate with valid input
  let g = http.post(`${BASE}/generate`, PAYLOAD, { headers: HEADERS });
  apiLatency.add(g.timings.duration);
  let isSuccess = g.status === 200;
  let isLimited = g.status === 429;
  check(g, {
    'generate accepts or rate-limits': (r) => isSuccess || isLimited,
    'generate returns JSON': (r) => r.json('message') !== undefined || r.json('error') !== undefined,
  });
  errorRate.add(!isSuccess && !isLimited);
  if (isLimited) rateLimited.add(1);

  // 3. Invalid input (should pass through — no LLM call, no rate limit)
  let b = http.post(`${BASE}/generate`, JSON.stringify({
    company_name: '',
    job_description: '',
  }), { headers: HEADERS });
  check(b, { 'bad input 400': (r) => r.status === 400 });

  // 4. 404 route
  let n = http.get(`${BASE}/nonexistent`);
  check(n, { 'not found 404': (r) => r.status === 404 });

  sleep(0.5);
}
