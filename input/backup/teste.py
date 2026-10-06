from services.text_engines.lexical_analyzer import LexicalAnalyzer
from services.text_engines.clause_analyzer import ClauseAnalyzer
from services.text_engines.speech_block_builder import SpeechBlockBuilder
from services.text_engines.pause_planner import PausePlanner
from services.text_engines.ssml_engine import SSMLEngine

# load text
text = open("input/script.txt", encoding="utf-8").read()

# 1. Lexical
lex = LexicalAnalyzer()
tokens = lex.tokenize(text)

# 2. Clause
clause_engine = ClauseAnalyzer()
clauses = clause_engine.analyze(tokens)

# 3. Speech Blocks
builder = SpeechBlockBuilder()
blocks = builder.build(clauses)

# 4. Pause Planner
planner = PausePlanner()
clauses = planner.plan(clauses)

# 5. SSML
ssml_engine = SSMLEngine()
ssml = ssml_engine.build(clauses)

print("\n===== BLOCKS =====\n")
print(blocks)

print("\n===== SSML =====\n")
print(ssml)