const clients = new Set();

function buildPayload(teachers) {
  return JSON.stringify({
    type: 'attendance:update',
    timestamp: new Date().toISOString(),
    teachers
  });
}

function addClient(res) {
  clients.add(res);
}

function removeClient(res) {
  clients.delete(res);
}

function publishTeachers(teachers) {
  const payload = buildPayload(teachers);
  for (const client of clients) {
    client.write(`event: attendance\n`);
    client.write(`data: ${payload}\n\n`);
  }
}

module.exports = {
  addClient,
  removeClient,
  publishTeachers
};
