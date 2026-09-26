namespace IlPayload;

public static class EntryPoint
{
    public static string Run()
    {
        var box = new GenericBox<int>(40);
        box.Value += 2;
        return $"XAP_ILRUN1_PASS:{box.Value}";
    }

    private sealed class GenericBox<T>
    {
        public GenericBox(T value) => Value = value;
        public T Value { get; set; }
    }
}
