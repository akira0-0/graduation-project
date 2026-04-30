import sys
sys.path.insert(0, '.')
try:
    from src.agents.sentiment_agent import SentimentAnalysisAgent
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback; traceback.print_exc()
