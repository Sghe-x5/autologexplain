import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export const FormInput = ({
  className,
  "data-test-id": dataTestId = "form-input",
  ...props
}: React.ComponentProps<"input"> & { "data-test-id"?: string }) => {
  return (
    <Input
      {...props}
      data-test-id={dataTestId}
      className={cn(
        className,
        "hover:border-1 hover:border-[#2463EB] ease-in transition-all"
      )}
    />
  );
};
