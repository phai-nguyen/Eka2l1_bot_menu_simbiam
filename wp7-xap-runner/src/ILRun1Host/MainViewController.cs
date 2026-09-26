using CoreGraphics;
using UIKit;

namespace WP7ILRun1;

internal sealed class MainViewController : UIViewController
{
    private UITextView? _logView;
    private UILabel? _statusLabel;
    private bool _ranOnce;

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        View.BackgroundColor = UIColor.SystemBackground;

        var title = new UILabel(new CGRect(16, 54, View.Bounds.Width - 32, 34))
        {
            Text = "WP7 XAP Runner — ILRUN1",
            Font = UIFont.BoldSystemFontOfSize(22),
            AutoresizingMask = UIViewAutoresizing.FlexibleWidth
        };
        View.AddSubview(title);

        _statusLabel = new UILabel(new CGRect(16, 94, View.Bounds.Width - 32, 28))
        {
            Text = "Chưa chạy",
            Font = UIFont.SystemFontOfSize(16),
            AutoresizingMask = UIViewAutoresizing.FlexibleWidth
        };
        View.AddSubview(_statusLabel);

        _logView = new UITextView(new CGRect(12, 130, View.Bounds.Width - 24, View.Bounds.Height - 250))
        {
            Editable = false,
            Font = UIFont.MonospacedSystemFontOfSize(11, UIFontWeight.Regular),
            AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight,
            Text = "[ILRUN1][UI_READY]\n"
        };
        View.AddSubview(_logView);

        var runButton = UIButton.FromType(UIButtonType.System);
        runButton.Frame = new CGRect(16, View.Bounds.Height - 104, (View.Bounds.Width - 44) / 2, 44);
        runButton.SetTitle("Chạy lại IL", UIControlState.Normal);
        runButton.AutoresizingMask = UIViewAutoresizing.FlexibleTopMargin | UIViewAutoresizing.FlexibleRightMargin;
        runButton.TouchUpInside += (_, _) => RunProbe();
        View.AddSubview(runButton);

        var copyButton = UIButton.FromType(UIButtonType.System);
        copyButton.Frame = new CGRect(28 + (View.Bounds.Width - 44) / 2, View.Bounds.Height - 104, (View.Bounds.Width - 44) / 2, 44);
        copyButton.SetTitle("Sao chép log", UIControlState.Normal);
        copyButton.AutoresizingMask = UIViewAutoresizing.FlexibleTopMargin | UIViewAutoresizing.FlexibleLeftMargin;
        copyButton.TouchUpInside += (_, _) =>
        {
            UIPasteboard.General.String = _logView?.Text ?? string.Empty;
            if (_statusLabel is not null)
                _statusLabel.Text = "Đã sao chép log";
        };
        View.AddSubview(copyButton);
    }

    public override void ViewDidAppear(bool animated)
    {
        base.ViewDidAppear(animated);
        if (_ranOnce)
            return;

        _ranOnce = true;
        RunProbe();
    }

    private void RunProbe()
    {
        if (_logView is null || _statusLabel is null)
            return;

        _statusLabel.Text = "Đang chạy ILRUN1…";
        _logView.Text = string.Empty;

        var result = IlRun1Executor.Execute(line =>
        {
            _logView.Text += line + "\n";
            _logView.ScrollRangeToVisible(new Foundation.NSRange(_logView.Text.Length, 0));
        });

        _statusLabel.Text = result.Success
            ? "PASS — external managed IL đã chạy"
            : "FAIL — sao chép log gửi lại";
    }
}
