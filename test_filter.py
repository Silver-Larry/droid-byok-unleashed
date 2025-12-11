"""Unit tests for the StreamFilter class."""

import sys
sys.path.insert(0, "D:\\demo\\droid-byok-unleashed")

from proxy import StreamFilter


def test_basic_filtering():
    """Test basic <think> block filtering."""
    sf = StreamFilter()
    
    # Simple case
    output, thinking = sf.process_chunk("Hello <think>internal thought</think> World")
    assert output == "Hello  World", f"Expected 'Hello  World', got '{output}'"
    assert thinking == "internal thought", f"Expected 'internal thought', got '{thinking}'"
    print("[PASS] Basic filtering")


def test_split_tag_start():
    """Test <think> tag split across chunks."""
    sf = StreamFilter()
    
    # Tag split: "<thi" + "nk>content</think>"
    out1, think1 = sf.process_chunk("Hello <thi")
    out2, think2 = sf.process_chunk("nk>thinking here</think> World")
    
    assert out1 == "Hello ", f"Expected 'Hello ', got '{out1}'"
    assert out2 == " World", f"Expected ' World', got '{out2}'"
    assert think2 == "thinking here", f"Expected 'thinking here', got '{think2}'"
    print("[PASS] Split tag start")


def test_split_tag_end():
    """Test </think> tag split across chunks."""
    sf = StreamFilter()
    
    # Tag split: "<think>content</thi" + "nk>rest"
    out1, think1 = sf.process_chunk("Start <think>thought</thi")
    out2, think2 = sf.process_chunk("nk> End")
    
    assert out1 == "Start ", f"Expected 'Start ', got '{out1}'"
    assert out2 == " End", f"Expected ' End', got '{out2}'"
    assert "thought" in think1 or "thought" in think2
    print("[PASS] Split tag end")


def test_multiple_chunks_inside_think():
    """Test multiple chunks while inside <think> block."""
    sf = StreamFilter()
    
    out1, think1 = sf.process_chunk("Hello <think>first ")
    out2, think2 = sf.process_chunk("second ")
    out3, think3 = sf.process_chunk("third</think> World")
    
    assert out1 == "Hello ", f"Expected 'Hello ', got '{out1}'"
    assert out2 == "", f"Expected '', got '{out2}'"
    assert out3 == " World", f"Expected ' World', got '{out3}'"
    assert think1 == "first "
    assert think2 == "second "
    assert think3 == "third"
    print("[PASS] Multiple chunks inside think")


def test_no_think_tags():
    """Test content without any <think> tags."""
    sf = StreamFilter()
    
    output, thinking = sf.process_chunk("Just normal content here")
    assert output == "Just normal content here"
    assert thinking == ""
    print("[PASS] No think tags")


def test_empty_think_block():
    """Test empty <think></think> block."""
    sf = StreamFilter()
    
    output, thinking = sf.process_chunk("Before <think></think> After")
    assert output == "Before  After"
    assert thinking == ""
    print("[PASS] Empty think block")


def test_flush():
    """Test flushing remaining buffer."""
    sf = StreamFilter()
    
    # Partial tag at end
    out1, _ = sf.process_chunk("Content <thi")
    remaining, _ = sf.flush()
    
    # Buffer should be flushed
    assert remaining == "<thi" or out1 + remaining == "Content <thi"
    print("[PASS] Flush")


if __name__ == "__main__":
    print("Running StreamFilter tests...\n")
    
    test_basic_filtering()
    test_split_tag_start()
    test_split_tag_end()
    test_multiple_chunks_inside_think()
    test_no_think_tags()
    test_empty_think_block()
    test_flush()
    
    print("\n[ALL TESTS PASSED]")
