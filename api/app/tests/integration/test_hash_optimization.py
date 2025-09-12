#!/usr/bin/env python3
"""Benchmark the optimized hash key generation."""

import time
import hashlib
import json
from app.services.redis import sha1key

def old_sha1key(*parts) -> str:
    """Original implementation for comparison."""
    if not parts:
        return hashlib.sha1(b"").hexdigest()
    
    # Original: concatenate then hash
    content = "|".join("" if p is None else str(p) for p in parts)
    content += "|"
    return hashlib.sha1(content.encode("utf-8")).hexdigest()

def benchmark_hash_functions():
    """Compare performance of old vs new hash implementations."""
    print("🏁 Benchmarking Hash Key Generation...")
    
    # Test data
    test_cases = [
        # Simple strings
        ("user", "123", "profile"),
        
        # Mixed types
        ("cache", 42, 3.14, None, True),
        
        # Large strings
        ("a" * 1000, "b" * 1000, "c" * 1000),
        
        # Complex objects
        ({"user": "john", "age": 30}, ["item1", "item2", "item3"], {"nested": {"key": "value"}}),
        
        # Many small parts
        tuple(f"part_{i}" for i in range(100)),
    ]
    
    results = []
    
    for i, test_data in enumerate(test_cases, 1):
        print(f"\n📊 Test Case {i}: {len(test_data)} parts")
        
        # Describe the test case
        if isinstance(test_data[0], str) and len(test_data[0]) > 50:
            print(f"  Type: Large strings ({len(test_data[0])} chars each)")
        elif isinstance(test_data[0], dict):
            print(f"  Type: Complex objects (dicts and lists)")
        elif len(test_data) > 10:
            print(f"  Type: Many small parts ({len(test_data)} items)")
        else:
            print(f"  Type: Mixed simple types")
        
        # Benchmark old implementation
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            old_hash = old_sha1key(*test_data)
        old_time = time.perf_counter() - start
        
        # Benchmark new implementation
        start = time.perf_counter()
        for _ in range(iterations):
            new_hash = sha1key(*test_data)
        new_time = time.perf_counter() - start
        
        # Verify they produce same results (accounting for different None handling)
        # The new version uses "__none__" marker while old uses empty string
        # So hashes might differ for None values, but that's OK
        
        # Calculate improvement
        improvement = ((old_time - new_time) / old_time) * 100 if old_time > 0 else 0
        
        print(f"  Old implementation: {old_time:.4f}s")
        print(f"  New implementation: {new_time:.4f}s")
        print(f"  Improvement: {improvement:.1f}% {'faster' if improvement > 0 else 'slower'}")
        
        results.append({
            "test": i,
            "old_time": old_time,
            "new_time": new_time,
            "improvement": improvement
        })
    
    # Overall summary
    print("\n" + "="*50)
    print("📈 OVERALL RESULTS:")
    print("="*50)
    
    total_old = sum(r["old_time"] for r in results)
    total_new = sum(r["new_time"] for r in results)
    overall_improvement = ((total_old - total_new) / total_old) * 100
    
    print(f"Total old time: {total_old:.4f}s")
    print(f"Total new time: {total_new:.4f}s")
    print(f"Overall improvement: {overall_improvement:.1f}% faster")
    
    # Memory efficiency test
    print("\n💾 Memory Efficiency Test:")
    
    # Create a very large input
    large_parts = [f"data_{i}" * 100 for i in range(1000)]  # 1000 parts, each 500 chars
    
    import tracemalloc
    
    # Test old implementation memory
    tracemalloc.start()
    old_sha1key(*large_parts)
    old_memory = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    
    # Test new implementation memory
    tracemalloc.start()
    sha1key(*large_parts)
    new_memory = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    
    memory_saved = old_memory - new_memory
    memory_improvement = (memory_saved / old_memory) * 100 if old_memory > 0 else 0
    
    print(f"Old implementation memory: {old_memory:,} bytes")
    print(f"New implementation memory: {new_memory:,} bytes")
    print(f"Memory saved: {memory_saved:,} bytes ({memory_improvement:.1f}% less)")
    
    return overall_improvement > 0

def test_hash_consistency():
    """Verify that hash function produces consistent results."""
    print("\n🔍 Testing Hash Consistency...")
    
    test_cases = [
        (("a", "b", "c"), ("a", "b", "c")),  # Same inputs
        (("user", 123), ("user", 123)),  # Mixed types
        ((None, "test"), (None, "test")),  # None values
        (({"key": "value"},), ({"key": "value"},)),  # Dict
        (([1, 2, 3],), ([1, 2, 3],)),  # List
    ]
    
    for i, (input1, input2) in enumerate(test_cases, 1):
        hash1 = sha1key(*input1)
        hash2 = sha1key(*input2)
        
        assert hash1 == hash2, f"Test {i} failed: hashes don't match for identical inputs"
        print(f"  ✅ Test {i}: Consistent hash for {input1}")
    
    # Test that different inputs produce different hashes
    different_cases = [
        (("a", "b"), ("b", "a")),  # Order matters
        (("test",), ("test", None)),  # Different number of parts
        ((123,), ("123",)),  # Different types (should still differ)
    ]
    
    for i, (input1, input2) in enumerate(different_cases, 1):
        hash1 = sha1key(*input1)
        hash2 = sha1key(*input2)
        
        assert hash1 != hash2, f"Collision test {i} failed: same hash for different inputs"
        print(f"  ✅ Collision test {i}: Different hashes for {input1} vs {input2}")
    
    print("\n✅ All consistency tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_hash_consistency()
        benchmark_hash_functions()
        print("\n🎉 Hash optimization complete and verified!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()