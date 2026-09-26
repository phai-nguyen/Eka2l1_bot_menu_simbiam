using Foundation;
using UIKit;

namespace WP7ILRun1;

[Register("AppDelegate")]
public sealed class AppDelegate : UIApplicationDelegate
{
    public override UIWindow? Window { get; set; }

    public override bool FinishedLaunching(UIApplication application, NSDictionary? launchOptions)
    {
        Window = new UIWindow(UIScreen.MainScreen.Bounds)
        {
            RootViewController = new MainViewController()
        };
        Window.MakeKeyAndVisible();
        return true;
    }
}
