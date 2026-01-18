use hf_hub::api::sync::Api;

fn main() -> anyhow::Result<()> {
    let api = Api::new()?;
    let repo = api.model("TheBloke/Llama-2-7B-Chat-AWQ".to_string());
    println!("Fetching config.json...");
    let path = repo.get("config.json")?;
    println!("Path: {:?}", path);
    Ok(())
}
