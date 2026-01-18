use redis::Client;
use shared::AppConfig;
use anyhow::Result;

#[derive(Clone)]
pub struct RedisService {
    pub client: Client,
}

impl RedisService {
    pub async fn new(config: &AppConfig) -> Result<Self> {
        let client = Client::open(config.redis_url.as_str())?;
        Ok(Self { client })
    }

    pub async fn get_connection(&self) -> Result<redis::aio::Connection> {
        let conn = self.client.get_async_connection().await?;
        Ok(conn)
    }
}
