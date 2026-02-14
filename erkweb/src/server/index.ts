import express from 'express';

import localPlansRouter from './routes/local-plans.js';
import plansRouter from './routes/plans.js';

const app = express();

app.use(express.json());
app.use('/api', plansRouter);
app.use('/api', localPlansRouter);

const PORT = parseInt(process.env.ERKWEB_PORT || '3001', 10);
app.listen(PORT, () => {
  console.log(`erkweb server listening on http://localhost:${PORT}`);
});
