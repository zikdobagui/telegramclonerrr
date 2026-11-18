import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from group_campaigns import CampaignConnectionPool, TelegramCampaignGateway


class ConnectionPoolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = CampaignConnectionPool()

    async def asyncTearDown(self):
        self.pool.loop.call_soon_threadsafe(self.pool.loop.stop)
        self.pool.thread.join(2)
        self.pool.loop.close()

    async def test_shared_connection_survives_first_task_pause(self):
        first = self.pool.attach(TelegramCampaignGateway({}, {'same': {}}, (1, 'test')))
        second = self.pool.attach(TelegramCampaignGateway({}, {'same': {}}, (1, 'test')))
        client = SimpleNamespace(disconnect=AsyncMock())
        self.pool.clients['same'] = client
        self.assertIs(first.clients, second.clients)
        await first.close()
        client.disconnect.assert_not_awaited()
        self.assertIn('same', second.clients)
        await second.close()
        client.disconnect.assert_awaited_once()
        self.assertEqual(self.pool.clients, {})

    async def test_operations_use_one_loop_and_queue_without_overlap(self):
        active = 0
        peak = 0
        loops = []
        class Gateway:
            sessions = {'same': {}}
            async def invite(self):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                loops.append(asyncio.get_running_loop())
                await asyncio.sleep(0.01)
                active -= 1
                return True
            async def close(self):
                pass
        first = self.pool.attach(Gateway())
        second = self.pool.attach(Gateway())
        self.assertEqual(await asyncio.gather(first.invite(), second.invite()), [True, True])
        self.assertEqual(peak, 1)
        self.assertTrue(all(loop is self.pool.loop for loop in loops))
        await first.close()
        await second.close()
