/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useForm } from "react-hook-form";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceAIConfigurationKeys } from "@plane/types";
import { Input } from "@plane/ui";
// components
import { ControllerInput } from "@/components/common/controller-input";
// hooks
import { useInstance } from "@/hooks/store";

type IInstanceAIForm = {
  config: IFormattedInstanceConfiguration;
};

type AIFormValues = Record<TInstanceAIConfigurationKeys, string>;

type ProviderId = "openrouter" | "bedrock" | "azure" | "litellm";

const PROVIDERS: {
  id: ProviderId;
  label: string;
  description: string;
  baseUrl: string;
  models: string[];
  keyHelp: string;
}[] = [
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "One API key for many cloud models.",
    baseUrl: "https://openrouter.ai/api/v1",
    models: ["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"],
    keyHelp: "OpenRouter API key from openrouter.ai/keys",
  },
  {
    id: "bedrock",
    label: "AWS Bedrock",
    description: "Routed through LiteLLM. AWS keys stay in server env.",
    baseUrl: "http://litellm:4000/v1",
    models: [
      "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
      "bedrock/amazon.nova-lite-v1:0",
      "bedrock/amazon.nova-pro-v1:0",
    ],
    keyHelp: "LiteLLM master key (same value as LITELLM_MASTER_KEY)",
  },
  {
    id: "azure",
    label: "Azure OpenAI",
    description: "Your Azure endpoint, deployment, and key.",
    baseUrl: "",
    models: ["azure/gpt-4o-mini", "azure/gpt-4o"],
    keyHelp: "Azure API key, or the LiteLLM master key if routing through the gateway",
  },
  {
    id: "litellm",
    label: "LiteLLM gateway",
    description: "Use the on-host gateway and pick any configured model.",
    baseUrl: "http://litellm:4000/v1",
    models: [
      "openrouter/openai/gpt-4o-mini",
      "openrouter/anthropic/claude-3.5-sonnet",
      "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
      "azure/gpt-4o-mini",
    ],
    keyHelp: "LiteLLM master key",
  },
];

function providerFor(value: string | undefined): (typeof PROVIDERS)[number] {
  return PROVIDERS.find((item) => item.id === value) ?? PROVIDERS[0];
}

export function InstanceAIForm(props: IInstanceAIForm) {
  const { config } = props;
  const { updateInstanceConfigurations } = useInstance();
  const {
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AIFormValues>({
    defaultValues: {
      LLM_PROVIDER: config["LLM_PROVIDER"] || "openrouter",
      LLM_MODEL: config["LLM_MODEL"] || "openai/gpt-4o-mini",
      LLM_API_KEY: config["LLM_API_KEY"] || "",
      LLM_BASE_URL: config["LLM_BASE_URL"] || "https://openrouter.ai/api/v1",
    },
  });

  const providerId = (watch("LLM_PROVIDER") || "openrouter") as ProviderId;
  const provider = providerFor(providerId);
  const model = watch("LLM_MODEL") || "";
  const modelChoices = provider.models.includes(model) ? provider.models : [model, ...provider.models].filter(Boolean);

  const onProviderChange = (nextId: string) => {
    const next = providerFor(nextId);
    setValue("LLM_PROVIDER", next.id);
    setValue("LLM_BASE_URL", next.baseUrl);
    if (!next.models.includes(watch("LLM_MODEL"))) {
      setValue("LLM_MODEL", next.models[0] ?? "");
    }
  };

  const onSubmit = async (formData: AIFormValues) => {
    await updateInstanceConfigurations(formData)
      .then(() =>
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Success",
          message: "AI settings updated",
        })
      )
      .catch((err) => console.error(err));
  };

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <div className="pb-1 text-18 font-medium text-primary">Cloud provider</div>
          <div className="text-13 font-regular text-tertiary">
            OpenRouter, AWS Bedrock, and Azure OpenAI. Plane calls the base URL with the API key and model below.
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {PROVIDERS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onProviderChange(item.id)}
              className={`rounded-md border px-4 py-3 text-left ${
                providerId === item.id ? "border-accent-strong bg-accent-subtle" : "border-subtle bg-layer-1"
              }`}
            >
              <div className="text-13 font-medium text-primary">{item.label}</div>
              <div className="text-11 text-tertiary">{item.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid w-full grid-cols-1 items-start gap-x-12 gap-y-8 lg:grid-cols-2">
        <div className="flex flex-col gap-1">
          <h4 className="text-13 text-tertiary">Model</h4>
          <Controller
            control={control}
            name="LLM_MODEL"
            render={({ field: { value, onChange } }) => (
              <select
                className="h-9 w-full rounded-md border border-subtle bg-layer-1 px-3 text-13 text-primary"
                value={value}
                onChange={(event) => onChange(event.target.value)}
              >
                {modelChoices.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            )}
          />
          <Input
            className="mt-2 w-full rounded-md font-medium"
            placeholder="Or type a model id your key can call"
            value={model}
            onChange={(event) => setValue("LLM_MODEL", event.target.value)}
          />
          {errors.LLM_MODEL ? <span className="text-11 text-danger-primary">Model is required.</span> : null}
        </div>

        <ControllerInput
          control={control}
          type="password"
          name="LLM_API_KEY"
          label="API key"
          description={provider.keyHelp}
          placeholder="sk-..."
          error={Boolean(errors.LLM_API_KEY)}
          required={false}
        />

        <div className="flex flex-col gap-1 lg:col-span-2">
          <h4 className="text-13 text-tertiary">Base URL</h4>
          <Controller
            control={control}
            name="LLM_BASE_URL"
            render={({ field: { value, onChange, ref } }) => (
              <Input
                id="LLM_BASE_URL"
                name="LLM_BASE_URL"
                type="text"
                value={value}
                onChange={onChange}
                ref={ref}
                placeholder={provider.baseUrl || "https://your-resource.openai.azure.com/openai/v1"}
                className="w-full rounded-md font-medium"
              />
            )}
          />
          <p className="text-11 text-tertiary">
            OpenRouter: https://openrouter.ai/api/v1. Gateway on this server: http://litellm:4000/v1. Azure: your
            resource endpoint.
          </p>
        </div>
      </div>

      <Button variant="primary" size="lg" onClick={handleSubmit(onSubmit)} loading={isSubmitting}>
        {isSubmitting ? "Saving" : "Save changes"}
      </Button>
    </div>
  );
}
