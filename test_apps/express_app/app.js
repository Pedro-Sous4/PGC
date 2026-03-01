const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('<h1>Express Test App</h1><p>Express is working!</p>');
});

app.listen(port, () => {
  console.log(`Express app listening at http://localhost:${port}`);
});